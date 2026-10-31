"""Reviewed application identity, separate from configured model provenance."""
import re

PROJECT_URL = 'https://github.com/n8storm/Zenith'
PROJECT_IDENTITY = "I'm Zenith, maintained by n8storm in the Zenith open-source project."
IDENTITY_POLICY = (
    'Your application name is Zenith, maintained by n8storm. '
    'Distinguish this application from its configured foundation model and its original developer. '
    'Do not invent a different application name or claim another organization created Zenith. '
)
KNOWN_FOUNDATIONS = {
    'Qwen/Qwen2.5-0.5B-Instruct': "Alibaba Cloud's Qwen team",
}
SELF_QUESTION = re.compile(
    r"(?:please |tell me |please tell me |can you tell me |do you know )?"
    r"(?:who (?:created|made|built|developed|designed) (?:you|zenith)|"
    r"who (?:is|are) your (?:creator|creators|developer|developers)|"
    r"who are you|what (?:is|are) you|what is your name|what's your name|"
    r"what (?:model|ai) are you|what model (?:do you use|are you using)|"
    r"are you (?:zeno|zenith|qwen|chatgpt|claude)|introduce yourself|"
    r"what is your name and who (?:created|made|developed) you)\Z"
)
SELF_REFERENCE = re.compile(
    r"\b(?:who (?:created|made|built|developed|designed) (?:you|zenith)|"
    r"your (?:name|creator|creators|developer|developers|foundation model)|"
    r"what model (?:are you|do you use)|(?:are|were) you (?:zeno|zenith|qwen|chatgpt|claude))\b"
)


def needs_identity_context(text):
    if not isinstance(text, str) or '```' in text:
        return False
    if re.match(r'\s*(?:translate|rewrite|paraphrase|quote|extract)\b',text,re.I):
        return False
    return bool(SELF_REFERENCE.search(text.casefold()))


def model_provenance(settings):
    if settings is None:
        return 'Foundation-model provenance depends on the configured inference backend.'
    if settings.provider == 'huggingface':
        model = settings.model
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', model):
            return 'This deployment uses a configured Hugging Face model; its upstream developer is not verified in this identity metadata.'
        developer = KNOWN_FOUNDATIONS.get(model)
        text = 'The configured foundation model is ' + model
        text += ', developed by ' + developer if developer else '; its upstream developer is not verified in this identity metadata'
        if settings.adapter:
            text += ', with a configured Zenith adapter'
        return text + '.'
    descriptions = {
        'tiny': "This deployment uses Zenith's experimental Tiny model.",
        'ollama': 'This deployment uses an Ollama backend; upstream model authorship must be verified separately.',
        'localserver': 'This deployment uses a local inference server; upstream model authorship must be verified separately.',
        'ensemble': 'This deployment uses a configured model team; foundation-model authorship depends on its configured members.',
        'orchestrated': 'This deployment uses model routing; foundation-model authorship depends on the selected backend.',
        'reasoning': 'This deployment uses a reasoning harness; foundation-model authorship depends on the selected backend.',
    }
    return descriptions.get(settings.provider, 'Foundation-model provenance is not verified by this interface.')


def identity_answer(text, settings=None):
    if not isinstance(text, str) or len(text) > 200:
        return None
    question = ' '.join(text.casefold().replace('\u2019', "'").split()).rstrip(' .?!')
    if not SELF_QUESTION.fullmatch(question):
        return None
    return {'text': PROJECT_IDENTITY + ' ' + model_provenance(settings),
            'abstained':False, 'method':'application-identity', 'source':PROJECT_URL}
