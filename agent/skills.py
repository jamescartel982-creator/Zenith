"""Offline, versioned learning profiles with workflows and source references.

Profiles guide a configured model. They do not execute tools, train weights, or
establish professional qualifications. External resources are never fetched by
selecting a profile or opening the library.
"""
import argparse
from copy import deepcopy
from datetime import date
from functools import lru_cache
from importlib.resources import files
import json
import re
from urllib.parse import urlsplit


CATEGORIES = {'general': 'Conversation skills', 'security': 'Security · administrator'}
_ID = re.compile(r'[a-z][a-z0-9-]{0,39}\Z')
PROFILE_SCOPE = (
    'Profiles grant no tools or privileges. Respect privacy and authorization. '
    'For security, support defense and authorized non-destructive assessment; '
    'decline malware deployment, theft, DDoS, doxxing, unauthorized exploitation, '
    'and retaliation. Offer remediation or an authorized lab alternative.'
)


def _text(value, label, maximum):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f'Invalid {label}')


def _texts(value, label, minimum=1, maximum=5, length=500):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError(f'Invalid {label}')
    for item in value:
        _text(item, label, length)


def _records(value, key, maximum):
    rows = value.get(key)
    if not isinstance(rows, list) or not 1 <= len(rows) <= maximum:
        raise ValueError(f'Invalid {key} collection')
    identifiers = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f'Invalid {key} record')
        identifier = row.get('id')
        if not isinstance(identifier, str) or not _ID.fullmatch(identifier) or identifier in identifiers:
            raise ValueError(f'Invalid or duplicate {key} identifier')
        identifiers.add(identifier)
    return rows, identifiers


def validate_profile(profile, resource_ids):
    if not isinstance(profile, dict) or not isinstance(profile.get("id"), str) or not _ID.fullmatch(profile["id"]):
        raise ValueError("Invalid profile identifier")
    for key, limit in [('name', 100), ('instruction', 700), ('deliverable', 600), ('practice', 600)]:
        _text(profile.get(key), f'profile {key}', limit)
    if profile.get('category') not in tuple(CATEGORIES) or profile.get('kind') != 'instruction-profile':
        raise ValueError('Invalid profile category or kind')
    expected_access = 'admin' if profile['category'] == 'security' else 'public'
    if profile.get('access') != expected_access:
        raise ValueError('Security profiles require admin access')
    if type(profile.get('version')) is not int or profile['version'] < 1:
        raise ValueError('Invalid profile version')
    _texts(profile.get('workflow'), 'profile workflow', minimum=3)
    _texts(profile.get('checklist'), 'profile checklist', minimum=2)
    _texts(profile.get('resource_ids'), 'profile resources', maximum=4, length=40)
    if len(set(profile['resource_ids'])) != len(profile['resource_ids']) or not set(profile['resource_ids']) <= resource_ids:
        raise ValueError('Profile references unknown or duplicate resources')

def validate_library(value):
    """Validate bundled metadata and references without network or model access."""
    if not isinstance(value, dict) or type(value.get('schema_version')) is not int or value['schema_version'] != 2:
        raise ValueError('Unsupported skill-library schema')
    _text(value.get('curated_on'), 'curation date', 10)
    try:
        date.fromisoformat(value['curated_on'])
    except ValueError as exc:
        raise ValueError('Invalid curation date') from exc
    _text(value.get('notice'), 'library notice', 1000)
    resources, resource_ids = _records(value, 'resources', 256)
    profiles, profile_ids = _records(value, 'skills', 256)
    taxonomy, _ = _records(value, 'taxonomy', 16)
    urls = set()
    for resource in resources:
        for key, limit in [('title', 180), ('publisher', 100), ('summary', 600), ('url', 2048)]:
            _text(resource.get(key), f'resource {key}', limit)
        if resource.get('category') not in tuple(CATEGORIES) or resource.get('kind') != 'learning-reference':
            raise ValueError('Invalid resource category or kind')
        url = resource['url']
        try:
            parsed = urlsplit(url)
            port = parsed.port
        except ValueError as exc:
            raise ValueError('Invalid resource URL') from exc
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                or parsed.hostname in {'localhost', '127.0.0.1', '::1'} or port not in {None, 443}
                or any(c.isspace() or ord(c) < 32 for c in url) or url in urls):
            raise ValueError('Resource URLs must be unique public HTTPS references without credentials')
        urls.add(url)
        verification = resource.get('verification')
        if not isinstance(verification, dict) or verification.get('status') not in ('retrieved', 'unavailable'):
            raise ValueError('Resource requires an explicit retrieval status')
        _text(verification.get('checked_on'), 'resource check date', 10)
        try:
            date.fromisoformat(verification['checked_on'])
        except ValueError as exc:
            raise ValueError('Invalid resource check date') from exc
        if verification['status'] == 'retrieved':
            status = verification.get('http_status')
            if type(status) is not int or not 200 <= status < 300:
                raise ValueError('Retrieved resource requires a successful HTTP status')
            _text(verification.get('page_title'), 'retrieved page title', 500)
    for profile in profiles:
        validate_profile(profile, resource_ids)
    for label in taxonomy:
        for key in ['name', 'meaning', 'professional_alternative']:
            _text(label.get(key), f'taxonomy {key}', 600)
        _texts(label.get('profile_ids'), 'taxonomy profiles', maximum=4, length=40)
        if not set(label['profile_ids']) <= profile_ids:
            raise ValueError('Taxonomy references unknown profiles')
    return {'ok': True, 'schema_version': 2, 'profiles': len(profiles), 'resources': len(resources),
            'admin_profiles': sum(p['access'] == 'admin' for p in profiles),
            'taxonomy_labels': len(taxonomy),
            'categories': {key: sum(row['category'] == key for row in profiles) for key in CATEGORIES},
            'unavailable_resources': [r['id'] for r in resources if r['verification']['status'] == 'unavailable'],
            'note': 'Offline metadata validation; resource availability is recorded, not checked live.'}


@lru_cache(maxsize=1)
def _library():
    raw = files('agent').joinpath('resources/skills-v1.json').read_bytes()
    if len(raw) > 512 * 1024:
        raise ValueError('Skill library exceeds its size limit')
    try:
        value = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        raise ValueError('Invalid skill-library JSON') from exc
    validate_library(value)
    return value


def _filter(rows, category, query, text_keys):
    if category is not None and category not in tuple(CATEGORIES):
        raise ValueError('Unknown skill category')
    if not isinstance(query, str) or len(query) > 200:
        raise ValueError('Search query must be at most 200 characters')
    query = query.strip().casefold()
    return [row for row in rows if (category is None or row['category'] == category)
            and (not query or query in ' '.join(str(row.get(key, '')) for key in text_keys).casefold())]


def list_skills(category=None, query='', *, include_admin=False):
    rows = [s for s in _library()['skills'] if include_admin or s['access'] == 'public']
    return deepcopy(_filter(rows, category, query, ['id', 'name', 'instruction', 'deliverable']))


def list_resources(category=None, query='', *, include_admin=False):
    used = {r for s in list_skills(include_admin=include_admin) for r in s['resource_ids']}
    rows = [r for r in _library()['resources'] if r['id'] in used]
    return deepcopy(_filter(rows, category, query, ['id', 'title', 'publisher', 'summary']))


def get_skill(identifier):
    for profile in _library()['skills']:
        if profile['id'] == identifier:
            result = deepcopy(profile)
            result['resources'] = deepcopy([r for r in _library()['resources'] if r['id'] in profile['resource_ids']])
            return result
    raise ValueError('Unknown skill')


def skills_library(*, include_admin=False):
    value = deepcopy(_library())
    value['skills'] = list_skills(include_admin=include_admin)
    value['resources'] = list_resources(include_admin=include_admin)
    value['taxonomy'] = value['taxonomy'] if include_admin else []
    value['categories'] = [{'id': key, 'name': name} for key, name in CATEGORIES.items()
                           if key == 'general' or include_admin]
    value['security_unlocked'] = include_admin
    value['validation'] = {'ok': True, 'profiles': len(value['skills']), 'resources': len(value['resources'])}
    return value


def skill_instruction(identifier):
    profile = get_skill(identifier)
    instruction = profile['instruction']
    if profile['category'] == 'security':
        instruction += '\nWorkflow: ' + ' '.join(profile['workflow'])
        instruction += '\nReview: ' + ' '.join(profile['checklist'][:2])
    if profile['category'] == 'security':
        instruction += '\n' + PROFILE_SCOPE
    return instruction


def main():
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='recipes':
        from .recipe_catalog import main as recipes_main
        return recipes_main(sys.argv[2:])
    if len(sys.argv)>1 and sys.argv[1] in {'import','remove-pack','search','capacity'}:
        from .skill_catalog import main as catalog_main
        return catalog_main(sys.argv[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for name in ['list', 'resources']:
        child = sub.add_parser(name)
        child.add_argument('--category', choices=list(CATEGORIES))
        child.add_argument('--query', default='')
    show = sub.add_parser('show')
    show.add_argument('identifier')
    for action in ('search','capacity','import','remove-pack'):
        sub.add_parser(action,help='Installed instruction-pack '+action+'; use '+action+' --help')
    sub.add_parser('recipes',help='Install, inspect or remove the labeled generated workflow recipe library')
    sub.add_parser('taxonomy')
    sub.add_parser('validate')
    args = parser.parse_args()
    try:
        if args.action == 'list':
            value = {'skills': list_skills(args.category, args.query)}
        elif args.action == 'resources':
            value = {'resources': list_resources(args.category, args.query)}
        elif args.action == 'show':
            try:value = get_skill(args.identifier)
            except ValueError:
                from .skill_catalog import SkillCatalog
                from .config import Settings
                from .storage import Store
                value=SkillCatalog(Store(Settings().data_dir)).get(args.identifier)
            if value['access'] == 'admin':
                raise ValueError('Unlock Admin in zenith chat to use security skills')
        elif args.action == 'taxonomy':
            value = {'notice': _library()['notice'], 'taxonomy': skills_library()['taxonomy']}
        else:
            value = validate_library(_library())
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(value, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
