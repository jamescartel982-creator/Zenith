"""Reconstruct an inactive research checkpoint without changing original files."""
import json
from pathlib import Path
import shutil
import tempfile
from .checkpoints import inventory
from .integrity import safe_source_path


def verify_bundle(bundle):
    bundle=Path(bundle).resolve()
    manifest=json.loads((bundle/'research.json').read_text(encoding='utf-8'))
    if manifest.get('schema_version')!=1 or manifest.get('approved_for_local_activation') is not False:
        raise ValueError('Expected an explicitly inactive research snapshot')
    observed=inventory(bundle);observed.pop('research.json',None)
    if observed!=manifest.get('files'):raise ValueError('Research snapshot files changed')
    return bundle,manifest


def materialize(bundle,output):
    bundle,manifest=verify_bundle(bundle);output=Path(output).expanduser().resolve()
    if output.exists() or output==bundle or bundle in output.parents or output in bundle.parents:
        raise ValueError('Use a new checkpoint directory outside the source bundle')
    source=safe_source_path(bundle,manifest['checkpoint'])
    parts=manifest['weight_parts']
    if not parts or len(parts)!=len(set(parts)):raise ValueError('Missing or duplicate weight parts')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.zenith-research-',dir=output.parent) as folder:
        candidate=Path(folder)/'checkpoint';shutil.copytree(source,candidate)
        weight=safe_source_path(candidate,manifest['weight_file'])
        with weight.open('xb') as handle:
            for part in parts:
                with safe_source_path(bundle,part).open('rb') as incoming:shutil.copyfileobj(incoming,handle)
        if inventory(candidate)!=manifest['checkpoint_files']:raise ValueError('Reconstructed checkpoint differs from the original')
        verify_bundle(bundle)
        candidate.rename(output)
    return {'checkpoint':str(output),'files':manifest['checkpoint_files'],'approved_for_local_activation':False}
