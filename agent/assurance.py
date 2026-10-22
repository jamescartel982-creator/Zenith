"""Conservative deterministic gates; no fabricated model-confidence probabilities."""
import re
import unicodedata
from .admin import contains_admin_code
from .tools import arithmetic_question


def normalize_input(text):
    text = unicodedata.normalize('NFKC',text).replace('\r\n','\n').replace('\r','\n')
    text = ''.join(c for c in text if unicodedata.category(c)!='Cf')
    if any(unicodedata.category(c)=='Cc' and c not in '\n\t' for c in text):
        raise ValueError('Remove control characters from your message')
    if contains_admin_code(text):
        raise ValueError('Enter your owner code in Admin → Unlock. It was not sent to a model or saved.')
    return text.strip()


def direct_answer(text, fast=True):
    words=text.casefold()
    devil=re.search(r'\bdevil\s*mode\b',words)
    if (devil and (re.search(r'\b(?:activate|unlock|enable|admin|administrator|permission|permissions|typing|chat|switch)\b',words) or words.strip()=='devil mode')) or (re.search(r'\b(?:typing|type|chat|prompt)\b',words) and re.search(r'\b(?:admin|administrator|privileges|elevation)\b',words)):
        return {'text':'No. Chat text cannot grant administrator permissions. Sign in as the owner account configured in your server terminal, then unlock Admin with your private local code. Devil mode opens only the bounded, authorized security workspace; it does not change model or machine permissions.', 'abstained':False, 'method':'application-authorization-fact'}
    if re.search(r'\b(?:reveal|show|tell|give)\b',words) and re.search(r'(?:admin(?:istrator)?|owner).{0,24}(?:code|secret|password)',words):
        return {'text':"I don't know your administrator code. It is generated privately on your machine and is never available to the model. Use the Admin panel and your local owner setup command.", 'abstained':True, 'method':'secret-unavailable'}
    if re.search(r'\bexact\b',words) and re.search(r'\b(?:birthday|birth date|date of birth|death date|date of death)\b',words) and not re.search(r'https?://',words):
        return {'text':"I don't know a verified exact date from a primary record available in this conversation. Please provide a reliable biographical source; I can help check it. I should not invent a precise day or month when the evidence is uncertain.", 'abstained':True, 'method':'precision-needs-evidence'}
    if re.search(r'\b(?:current|live|today|right now|latest)\b',words) and re.search(r'\b(?:stock|stocks|share|price|quote|aapl|tsla|btc|weather|news)\b',words):
        return {'text':"I don't know the current value because Zenith has no live market, weather, or news feed. Check a current primary source; I can help interpret data you provide.",'abstained':True,'method':'live-data-unavailable'}
    if re.search(r'\bguarantee(?:d)?\b',words) and re.search(r'\b(?:profit|profits|return|returns|win|winning)\b',words):
        return {'text':"I don't know any investment or trading strategy that guarantees profits. Losses, fees, slippage, leverage, and changing market conditions matter. A qualified professional can help review a real financial decision.",'abstained':True,'method':'unsupported-guarantee'}
    if fast:
        try: result=arithmetic_question(text)
        except ValueError as exc:
            return {'text':'I cannot evaluate that expression within the supported arithmetic rules: '+str(exc), 'abstained':True, 'method':'arithmetic-limit'}
        if result is not None: return {'text':result,'abstained':False,'method':'verified-arithmetic'}
    return None


def assurance(text, method='model', abstained=False, sources=0):
    human_review=bool(re.search(r'\b(?:invest|investment|trading|trade|medical|diagnos|legal|penetration|exploit|malware)\w*\b',text.casefold()))
    return {'method':method,'verification':'deterministic' if method=='verified-arithmetic' else 'not-verified',
            'abstained':abstained,'confidence':None,'calibration':'not-estimated',
            'needs_human_review':human_review,'retrieved_sources':sources,
            'note':'No calibrated confidence probability is available. Retrieved text and model agreement do not prove correctness.'}


def calibrated_assurance(settings, quality, mode):
    if not settings.calibration_file:return quality
    import json
    from pathlib import Path
    from .quality import configuration_signature
    try:
        path=Path(settings.calibration_file)
        if path.stat().st_size>65536:raise ValueError('Calibration file is oversized')
        artifact=json.loads(path.read_text(encoding='utf-8'))
        if artifact.get('configuration_sha256')!=configuration_signature(settings,mode):raise ValueError('Configuration mismatch')
        group=artifact['groups'].get(quality['method'])
        if not group or group['cases']<artifact['min_cases']:raise ValueError('Insufficient independent validation cases')
        if not 0<=group['wilson_lower']<=group['estimate']<=group['wilson_upper']<=1:raise ValueError('Invalid confidence bounds')
        quality={**quality,'confidence':group['estimate'],'confidence_lower_bound':group['wilson_lower'],
                 'calibration':'validation-method-group','note':artifact['warning']}
        if quality['method']=='model' and group['wilson_lower']<settings.abstain_threshold:
            quality.update(abstained=True,needs_human_review=True,method='validation-threshold-abstention')
        return quality
    except (OSError,ValueError,KeyError,TypeError):
        return {**quality,'calibration':'unavailable-or-mismatched','note':'No matching validated confidence artifact is available for this configuration.'}
