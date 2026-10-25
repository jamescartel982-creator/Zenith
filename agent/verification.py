"""Deterministic math, source-attribution checks and authorized restricted tests."""
from fractions import Fraction
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from .tools import calculate


def verify_math(expression, answer):
    expected = calculate(expression)
    text = answer.strip()
    if len(text) > 120 or not re.fullmatch(r'[+-]?\d+(?:\.\d+)?(?:/\d+)?', text):
        return {'status': 'failed', 'kind': 'exact-arithmetic', 'expected': expected, 'issue': 'Expected a numeric-only answer'}
    try:
        passed = Fraction(text) == Fraction(expected)
    except (ValueError, ZeroDivisionError):
        passed = False
    return {'status': 'passed' if passed else 'failed', 'kind': 'exact-arithmetic', 'expected': expected,
            'issue': None if passed else 'Answer differs from exact arithmetic'}


def verify_evidence(answer, sources):
    known = {s['url'] for s in sources}
    cited = set(re.findall(r'https?://[^\s<>"\]\)]+', answer))
    cited = {url.rstrip('.,;:') for url in cited}
    unknown = sorted(cited - known)
    labels = re.findall(r'\[S([^\]\s]{1,40})\]', answer)
    unknown_labels = [label for label in labels if not label.isascii() or not label.isdigit() or len(label) > 2 or not 1 <= int(label) <= len(sources)]
    return {'status': 'failed' if unknown or unknown_labels else 'attribution_checked' if cited or labels else 'unverified' if sources else 'not_requested',
            'unknown_citations': unknown, 'cited_sources': sorted(cited & known),
            'unknown_source_ids': unknown_labels,
            'claim_support': 'unverified', 'note': 'URL membership does not prove factual support or source credibility.'}


def run_restricted_tests(arguments):
    # Only called by ExecutionControls after explicit owner/MFA capability checks.
    if not isinstance(arguments, dict) or set(arguments) != {'source', 'entrypoint', 'cases'}:
        raise ValueError('Supply source, entrypoint and cases')
    raw = json.dumps(arguments, allow_nan=False).encode('utf-8')
    if len(raw) > 32768: raise ValueError('Restricted program input exceeds its budget')
    environment = {'SYSTEMROOT': os.environ['SYSTEMROOT']} if 'SYSTEMROOT' in os.environ else {}
    worker = str(Path(__file__).with_name('restricted_python.py').resolve())
    try:
        with tempfile.TemporaryDirectory(prefix='zenith-verify-') as folder:
            result = subprocess.run([sys.executable, '-I', '-S', '-X', 'utf8', worker], input=raw,
                capture_output=True, timeout=5, cwd=folder, env=environment, check=False)
    except subprocess.TimeoutExpired:
        return {'status': 'rejected', 'reason': 'Restricted interpreter exceeded its wall-time budget'}
    if result.returncode != 0 or len(result.stdout) > 32768:
        return {'status': 'rejected', 'reason': 'Restricted interpreter failed'}
    try:
        value = json.loads(result.stdout)
        if value.get('status') not in {'passed', 'failed', 'rejected'}: raise ValueError('Invalid worker status')
        return value
    except (ValueError, TypeError, AttributeError):
        return {'status': 'rejected', 'reason': 'Invalid restricted interpreter result'}


def verify_code(answer, specification, execution):
    if not isinstance(execution, dict) or set(execution) != {'controls', 'user_id', 'token'}:
        raise PermissionError('Code verification needs a trusted owner/MFA execution session')
    text = answer.strip()
    match = re.fullmatch(r'```(?:python)?\n([\s\S]*?)\n```', text)
    if match: text = match.group(1)
    return execution['controls'].execute(execution['user_id'], execution['token'], 'verify-python',
        {'source': text, 'entrypoint': specification['entrypoint'], 'cases': specification['cases']})
