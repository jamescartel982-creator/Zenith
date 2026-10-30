"""Save a portable per-user configuration without overwriting existing settings."""
import argparse
import os
import tempfile
from pathlib import Path
from .paths import config_file, zenith_home


def write_configuration(mode='local', path=None, overwrite=False):
    if mode not in {'local', 'ensemble', 'ollama', 'localserver'}:
        raise ValueError('Choose local, ensemble, ollama, or localserver mode')
    path = Path(path or config_file())
    if path.exists() and not overwrite:
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    provider = {'local': 'huggingface', 'ensemble': 'ensemble', 'ollama': 'ollama', 'localserver': 'localserver'}[mode]
    content = (
        '# Zenith user configuration. Environment variables and a checkout .env take precedence.\n'
        f'AI_PROVIDER={provider}\n'
        'HF_MODEL=Qwen/Qwen2.5-0.5B-Instruct\n'
        'HF_REVISION=7ae557604adf67be50417f59c2c2f167def9a775\n'
        'ZENITH_DEVICE=auto\nMAX_NEW_TOKENS=128\nCONTEXT_TOKENS=2048\n'
        'ZENITH_RESPONSE_MODE=fast\nZENITH_REPLY_STYLE=auto\nZENITH_FAST_MAX_NEW_TOKENS=96\nZENITH_FAST_HISTORY_TURNS=4\n'
        'TEMPERATURE=0.4\nOLLAMA_BASE_URL=http://localhost:11434\n'
        'OLLAMA_MODEL=qwen2.5-coder:7b\n'
        'ZENITH_LOCAL_SERVER_URL=http://127.0.0.1:8080/v1\nZENITH_LOCAL_SERVER_MODEL=zenith\n'
    )
    # Deliberately omit tokens and relative data paths. Fresh installs use the
    # stable user data directory; existing checkout .env/data stays in control.
    descriptor, temporary = tempfile.mkstemp(prefix='.zenith-config-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return path, True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['local', 'ensemble', 'ollama', 'localserver'], default='local')
    parser.add_argument('--overwrite', action='store_true', help='Explicitly replace the saved user profile')
    parser.add_argument('--activate-candidate',action='store_true',help='Explicitly accept known regressions and activate the bundled experimental candidate')
    parser.add_argument('--bundle',type=Path,default=Path.cwd()/'research_checkpoints'/'recovery-v1',help='Research bundle from the cloned repository')
    args = parser.parse_args()
    if args.activate_candidate:
        if args.mode!='local' or args.overwrite:parser.error('Candidate activation uses local mode and preserves the previous profile for rollback')
        from .deployment import use_research
        print('Activating the experimental candidate with known evaluation regressions. Restricted tools stay disabled.',flush=True)
        try:
            receipt=use_research(args.bundle,approve=True,allow_regressions=True,download_base=True,
                review_note='Operator explicitly requested setup --activate-candidate, accepting recorded quality regressions.')
        except (ValueError,OSError,KeyError) as exc:parser.error(str(exc))
        print('Activated '+receipt['id']+' ('+receipt['activation_status']+'). Numeric quality gate passed: '+str(receipt['numeric_gate_passed']))
        print('Run zenith serve --open-browser or zenith chat. Use zenith deployment status for the rollback receipt.')
        return 0
    path, created = write_configuration(args.mode, overwrite=args.overwrite)
    print(('Saved ' if created else 'Kept existing configuration: ') + str(path))
    print(f'Fresh-install data location: {zenith_home() / "data"}')
    print('Existing environment variables or a checkout .env can override this profile.')


if __name__ == '__main__':
    main()
