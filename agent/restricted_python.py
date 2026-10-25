"""Numeric Python-subset interpreter worker. Never eval/exec user source.

The host invokes this file with isolated Python in a temporary directory. This
worker has normal host process privileges; only its AST allowlist is exposed to
submitted programs. It is not a general Python or OS sandbox.
"""
import ast
import json
import math
import sys


class Rejected(ValueError):
    pass


def scalar(value):
    if type(value) not in {int, float, bool} or not math.isfinite(value) or abs(value) > 10**18:
        raise Rejected('Only finite bounded numeric and boolean scalars are supported')
    return value


class Interpreter:
    def __init__(self):
        self.steps = 0

    def tick(self):
        self.steps += 1
        if self.steps > 1000:
            raise Rejected('Program step budget exceeded')

    def expression(self, node, scope, depth=0):
        self.tick()
        if depth > 24:
            raise Rejected('Expression depth exceeded')
        visit = lambda item: self.expression(item, scope, depth + 1)
        if isinstance(node, ast.Constant):
            return scalar(node.value)
        if isinstance(node, ast.Name) and node.id in scope and not node.id.startswith('_'):
            return scope[node.id]
        if isinstance(node, ast.UnaryOp):
            value = visit(node.operand)
            if isinstance(node.op, ast.Not): return not value
            if isinstance(node.op, ast.UAdd): return scalar(+value)
            if isinstance(node.op, ast.USub): return scalar(-value)
        if isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add): value = left + right
            elif isinstance(node.op, ast.Sub): value = left - right
            elif isinstance(node.op, ast.Mult): value = left * right
            elif isinstance(node.op, ast.Div): value = left / right
            elif isinstance(node.op, ast.FloorDiv): value = left // right
            elif isinstance(node.op, ast.Mod): value = left % right
            elif isinstance(node.op, ast.Pow) and type(right) is int and abs(right) <= 12: value = left ** right
            else: raise Rejected('Unsupported arithmetic operator or exponent')
            return scalar(value)
        if isinstance(node, ast.Compare):
            left = visit(node.left)
            for operation, expression in zip(node.ops, node.comparators):
                right = visit(expression)
                if isinstance(operation, ast.Eq): passed = left == right
                elif isinstance(operation, ast.NotEq): passed = left != right
                elif isinstance(operation, ast.Lt): passed = left < right
                elif isinstance(operation, ast.LtE): passed = left <= right
                elif isinstance(operation, ast.Gt): passed = left > right
                elif isinstance(operation, ast.GtE): passed = left >= right
                else: raise Rejected('Unsupported comparison')
                if not passed: return False
                left = right
            return True
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                result = True
                for item in node.values:
                    result = visit(item)
                    if not result: return result
                return result
            if isinstance(node.op, ast.Or):
                result = False
                for item in node.values:
                    result = visit(item)
                    if result: return result
                return result
        if isinstance(node, ast.IfExp):
            return visit(node.body if visit(node.test) else node.orelse)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {'abs', 'min', 'max'} and not node.keywords and 1 <= len(node.args) <= 8:
            args = [visit(item) for item in node.args]
            if node.func.id == 'abs' and len(args) == 1: return scalar(abs(args[0]))
            if node.func.id == 'min' and len(args) >= 2: return min(args)
            if node.func.id == 'max' and len(args) >= 2: return max(args)
        raise Rejected('Unsupported expression')

    def statements(self, body, scope):
        for node in body:
            self.tick()
            if isinstance(node, ast.Return):
                return True, self.expression(node.value, scope)
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and not node.targets[0].id.startswith('_'):
                scope[node.targets[0].id] = self.expression(node.value, scope)
            elif isinstance(node, ast.If):
                returned, value = self.statements(node.body if self.expression(node.test, scope) else node.orelse, scope)
                if returned: return True, value
            elif not isinstance(node, ast.Assign):
                raise Rejected('Unsupported statement')
            else:
                raise Rejected('Unsupported assignment')
        return False, None


def check(payload):
    if not isinstance(payload, dict) or set(payload) != {'source', 'entrypoint', 'cases'}:
        raise Rejected('Supply source, entrypoint and cases')
    source, name, cases = payload['source'], payload['entrypoint'], payload['cases']
    if not isinstance(source, str) or not 1 <= len(source) <= 8192 or not isinstance(name, str) or not name.isidentifier() or name.startswith('_'):
        raise Rejected('Invalid bounded source or function name')
    if not isinstance(cases, list) or not 1 <= len(cases) <= 16:
        raise Rejected('Provide one to 16 numeric test cases')
    tree = ast.parse(source)
    if len(list(ast.walk(tree))) > 512 or len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise Rejected('Supply exactly one small numeric function')
    function = tree.body[0]; args = function.args
    if function.name != name or name in {'abs', 'min', 'max'} or function.decorator_list or function.returns or args.defaults or args.kw_defaults or args.vararg or args.kwarg or args.kwonlyargs or args.posonlyargs or not 0 <= len(args.args) <= 8 or any(a.annotation or a.arg.startswith('_') or a.arg in {'abs', 'min', 'max'} for a in args.args):
        raise Rejected('Unsupported function signature')
    names = [a.arg for a in args.args]
    if len(set(names)) != len(names): raise Rejected('Duplicate parameters')
    # Reject unsupported syntax even in branches that tests do not reach.
    allowed = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Assign, ast.If,
               ast.Constant, ast.Name, ast.Load, ast.Store, ast.UnaryOp, ast.BinOp, ast.BoolOp,
               ast.Compare, ast.IfExp, ast.Call, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
               ast.Mod, ast.Pow, ast.UAdd, ast.USub, ast.Not, ast.And, ast.Or, ast.Eq, ast.NotEq,
               ast.Lt, ast.LtE, ast.Gt, ast.GtE)
    if any(not isinstance(n, allowed) for n in ast.walk(tree)):
        raise Rejected('Program contains unsupported syntax')
    if sum(isinstance(n, ast.FunctionDef) for n in ast.walk(tree)) != 1 or any(
            isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and n.id in {'abs', 'min', 'max'} for n in ast.walk(tree)):
        raise Rejected('Nested functions and builtin shadowing are unsupported')
    if any(isinstance(n, ast.Name) and n.id.startswith('_') for n in ast.walk(tree)) or any(
            isinstance(n, ast.Call) and (not isinstance(n.func, ast.Name) or n.func.id not in {'abs', 'min', 'max'}) for n in ast.walk(tree)):
        raise Rejected('Unsupported names or function calls')
    results = []; interpreter = Interpreter()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {'args', 'expected'} or not isinstance(case['args'], list) or len(case['args']) != len(names):
            raise Rejected('Invalid numeric test case')
        values = [scalar(v) for v in case['args']]; expected = scalar(case['expected'])
        returned, actual = interpreter.statements(function.body, dict(zip(names, values)))
        if not returned: raise Rejected('Function must return a supported scalar')
        passed = actual == expected if type(expected) in {bool, int} else math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-12)
        results.append({'passed': passed, 'actual': actual})
    return {'status': 'passed' if all(r['passed'] for r in results) else 'failed', 'cases': results,
            'steps': interpreter.steps, 'runtime': 'restricted-numeric-python-subset', 'general_python_supported': False}


def main():
    try:
        data = sys.stdin.buffer.read(32769)
        if len(data) > 32768: raise Rejected('Input budget exceeded')
        result = check(json.loads(data))
    except (ValueError, TypeError, SyntaxError, ArithmeticError, RecursionError):
        result = {'status': 'rejected', 'reason': 'Unsupported or invalid bounded numeric program'}
    print(json.dumps(result, allow_nan=False))


if __name__ == '__main__': main()
