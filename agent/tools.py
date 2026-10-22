"""Small, bounded tools: no arbitrary shell, file access, or network access."""
import ast
import base64
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import ipaddress
import re
from urllib.parse import urlsplit


def calculate(expression):
    if not isinstance(expression, str) or not 1 <= len(expression) <= 120:
        raise ValueError('Use an arithmetic expression of at most 120 characters')
    try:
        tree = ast.parse(expression.strip(), mode='eval')
    except (SyntaxError, ValueError) as exc:
        raise ValueError('Use numbers, parentheses, +, -, *, / and small integer powers') from exc
    if len(list(ast.walk(tree))) > 40:
        raise ValueError('Expression is too complex')
    def visit(node, depth=0):
        if depth > 12:
            raise ValueError('Expression is too deeply nested')
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            value = Fraction(str(node.value))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand, depth+1) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
            left, right = visit(node.left, depth+1), visit(node.right, depth+1)
            if isinstance(node.op, ast.Add): value = left + right
            elif isinstance(node.op, ast.Sub): value = left - right
            elif isinstance(node.op, ast.Mult): value = left * right
            elif isinstance(node.op, ast.Div):
                if right == 0: raise ValueError('Division by zero is undefined')
                value = left / right
            else:
                if right.denominator != 1 or abs(right) > 12:
                    raise ValueError('Exponents must be integers between -12 and 12')
                if left == 0 and right < 0: raise ValueError('Division by zero is undefined')
                value = left ** int(right)
        else:
            raise ValueError('Only arithmetic is supported; names, calls, and attributes are not allowed')
        if abs(value) > 10**18 or value.denominator > 10**18:
            raise ValueError('Result exceeds the supported arithmetic range')
        return value
    value = visit(tree.body)
    if value.denominator == 1: return str(value.numerator)
    with localcontext() as context:
        context.prec = 24
        return format(Decimal(value.numerator) / Decimal(value.denominator), 'f').rstrip('0').rstrip('.')


def arithmetic_question(text):
    text = text.strip().casefold()
    text = re.sub(r'\s*(answer (?:briefly|with (?:just )?the (?:number|answer))\.?|give only the (?:number|answer)\.?)$', '', text).strip()
    text = re.sub(r'^(?:what is|calculate|compute|evaluate)\s+', '', text).rstrip('?. ')
    for word, operator in [('divided by', '/'), ('multiplied by', '*'), ('times', '*'), ('plus', '+'), ('minus', '-')]:
        text = re.sub(r'\b'+word+r'\b', operator, text)
    if not re.fullmatch(r'[\d\s.+*/()\-]{1,120}', text) or not re.search(r'[+*/-]', text):
        return None
    return calculate(text)


def code_audit(text):
    rules = [
        ('dynamic-execution', r'\b(?:eval|exec)\s*\(', 'Avoid evaluating untrusted input; use a strict parser or allowlist.'),
        ('shell-execution', r'\bshell\s*=\s*True', 'Pass explicit argument lists and validate inputs instead of invoking a shell.'),
        ('unsafe-deserialization', r'\bpickle\.(?:load|loads)\s*\(', 'Untrusted pickle data can execute code; choose a validated data format.'),
        ('disabled-tls-verification', r'\bverify\s*=\s*False', 'Keep TLS certificate verification enabled.'),
        ('possible-embedded-secret', r'(?i)(?:api_key|password|secret)\s*=\s*[\'"][^\'"\n]{8,}', 'Move secrets out of source and rotate any exposed value.'),
        ('weak-password-hash', r'\b(?:md5|sha1)\s*\(', 'Use a dedicated salted password KDF for passwords; context matters for non-password hashes.'),
    ]
    findings=[]
    for identifier, pattern, advice in rules:
        for match in re.finditer(pattern,text):
            findings.append({'rule':identifier,'line':text.count('\n',0,match.start())+1,'advice':advice})
    return {'findings':findings[:50], 'assurance':'Heuristic review only; absence of findings is not proof of security.'}


TOOLS = {
    'calculator': 'Bounded exact rational arithmetic with decimal output.',
    'sha256': 'SHA-256 digest of supplied text.',
    'decode-base64': 'Decode a small supplied Base64 string as UTF-8 text.',
    'code-audit': 'Offline heuristic security review of pasted code.',
    'inspect-url': 'Offline URL structure inspection; never contacts the destination.',
}


def run_tool(name, text):
    if not isinstance(text,str) or len(text)>12000:
        raise ValueError('Tool input must be text of at most 12000 characters')
    if name=='calculator': return {'result':calculate(text),'verification':'deterministic'}
    if name=='sha256': return {'sha256':hashlib.sha256(text.encode('utf-8')).hexdigest()}
    if name=='decode-base64':
        try: return {'text':base64.b64decode(text,validate=True).decode('utf-8')}
        except (ValueError,UnicodeError) as exc: raise ValueError('Input must be valid Base64 containing UTF-8 text') from exc
    if name=='code-audit': return code_audit(text)
    if name=='inspect-url':
        parsed=urlsplit(text)
        if parsed.scheme not in {'http','https'} or not parsed.hostname: raise ValueError('Enter an HTTP(S) URL')
        try: private=ipaddress.ip_address(parsed.hostname).is_private
        except ValueError: private=None
        return {'scheme':parsed.scheme,'hostname':parsed.hostname,'port':parsed.port,'contains_credentials':bool(parsed.username or parsed.password),'literal_private_ip':private,'network_request_made':False}
    raise ValueError('Unknown tool; arbitrary commands are not supported')
