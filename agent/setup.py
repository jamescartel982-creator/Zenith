"""Save a portable per-user configuration without overwriting existing settings."""
import argparse
from pathlib import Path
from .paths import config_file, zenith_home


def write_configuration(mode='local', path=None, overwrite=False):
    if mode not in {'local', 'ensemble', 'ollama'}:
        raise ValueError('Choose local, ensemble, or ollama mode')
    path = Path(path or config_file())
    if path.exists() and not overwrite:
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    provider = {'local': 'huggingface', 'ensemble': 'ensemble', 'ollama': 'ollama'}[mode]
    content = (
        '# Zenith user configuration. Environment variables and a checkout .env take precedence.\n'
        f'AI_PROVIDER={provider}\n'
        'HF_MODEL=Qwen/Qwen2.5-0.5B-Instruct\n'
        'HF_REVISION=7ae557604adf67be50417f59c2c2f167def9a775\n'
        'ZENITH_DEVICE=auto\nMAX_NEW_TOKENS=128\nCONTEXT_TOKENS=2048\n'
        'TEMPERATURE=0.4\nOLLAMA_BASE_URL=http://localhost:11434\n'
        'OLLAMA_MODEL=qwen2.5-coder:7b\n'
    )
    # Deliberately omit tokens and relative data paths. Fresh installs use the
    # stable user data directory; existing checkout .env/data stays in control.
    with path.open('w', encoding='utf-8', newline='\n') as handle:
        handle.write(content)
    try:
        path.chmod(0o600)
    except OSError:
        pass  # Windows ACLs govern access instead of POSIX mode bits.
    return path, True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['local', 'ensemble', 'ollama'], default='local')
    parser.add_argument('--overwrite', action='store_true', help='Explicitly replace the saved user profile')
    args = parser.parse_args()
    path, created = write_configuration(args.mode, overwrite=args.overwrite)
    print(('Saved ' if created else 'Kept existing configuration: ') + str(path))
    print(f'Fresh-install data location: {zenith_home() / "data"}')
    print('Existing environment variables or a checkout .env can override this profile.')


if __name__ == '__main__':
    main()
