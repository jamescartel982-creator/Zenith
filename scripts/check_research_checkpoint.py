"""Verify an inactive research snapshot and run real checkpoint inference."""
import argparse
import json
from pathlib import Path
from agent.checkpoints import inspect_checkpoint


def check(bundle):
    from agent.research import verify_bundle,materialize
    import tempfile
    bundle,manifest=verify_bundle(bundle)
    with tempfile.TemporaryDirectory(prefix='Zenith research verification ') as folder:
        checkpoint=Path(folder)/'checkpoint'
        materialize(bundle,checkpoint)
        measured=inspect_checkpoint(checkpoint)
        import gc;gc.collect()
    if measured['base_model']!=manifest['base_model'] or measured['base_revision']!=manifest['base_revision']:
        raise ValueError('Research model identity differs from its manifest')
    if measured['inference'].strip().rstrip('.') not in {'4','The answer is 4','2 + 2 = 4','2 plus 2 is 4'}:
        # This smoke test checks arithmetic on the actual model, not a mocked reply.
        import re
        if not re.search(r'(?<!\d)4(?!\d)',measured['inference']):raise ValueError('Research checkpoint failed basic inference')
    verify_bundle(bundle)
    return {'loaded_successfully':measured['loaded_successfully'],'base_model':measured['base_model'],
        'base_revision':measured['base_revision'],'base_parameters':measured['base_parameters'],
        'tokenizer_sha256':measured['tokenizer_sha256'],'inference':measured['inference'],
        'checkpoint_bytes':sum(v['bytes'] for v in measured['parent_files'].values()),
        'production_profile_changed':False,'restricted_tools_enabled':False,'approved_for_local_activation':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--bundle',type=Path,required=True)
    print(json.dumps(check(parser.parse_args().bundle),indent=2))


if __name__=='__main__':main()
