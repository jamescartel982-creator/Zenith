#!/usr/bin/env python3
"""Install Zenith in an isolated virtual environment on Windows or Linux.

Uses only the standard library until dependencies are installed. No activation,
administrator privileges, global PATH edits, or model download are required.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import venv
from agent.branding import show_banner

ROOT = Path(__file__).resolve().parent


def environment_python(directory):
    return Path(directory) / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def run(command, environment=None):
    parts = [str(part) for part in command]
    if parts[-3:] == ['-m', 'pip', 'check']:
        result = subprocess.run(parts, cwd=ROOT, env=environment, capture_output=True,
                                text=True, encoding='utf-8', errors='replace')
        if result.returncode:
            print(result.stdout, end='')
            print(result.stderr, end='', file=sys.stderr)
            result.check_returncode()
        print('Dependencies verified. No package conflicts detected.', flush=True)
    else:
        subprocess.run(parts, cwd=ROOT, env=environment, check=True)


def configured_provider(python):
    return subprocess.check_output(
        [str(python), '-c', 'from agent.config import Settings; print(Settings().provider)'],
        cwd=ROOT, text=True, encoding='utf-8').strip()


def configured_needs_hf(python):
    return subprocess.check_output(
        [str(python), '-c', 'from agent.models import model_specs; from agent.config import Settings; print(int(any(s["provider"] == "huggingface" for s in model_specs(Settings()))))'],
        cwd=ROOT, text=True, encoding='utf-8').strip() == '1'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['local', 'ensemble', 'ollama', 'localserver'], default='local')
    parser.add_argument('--venv', type=Path, default=ROOT / '.venv')
    parser.add_argument('--runtime', choices=['cpu', 'auto'], default='cpu', help='CPU wheels by default; auto uses the standard PyTorch distribution')
    parser.add_argument('--download', action='store_true', help='Also download the configured HF weights now')
    parser.add_argument('--launch', action='store_true', help='Download configured HF weights, then open browser chat after setup')
    parser.add_argument('--overwrite-config', action='store_true', help='Explicitly replace the saved user profile')
    args = parser.parse_args(argv)
    if sys.version_info < (3, 10):
        parser.error('Python 3.10+ is required; Python 3.12 is recommended')
    show_banner()
    target = args.venv.expanduser().resolve()
    python = environment_python(target)
    creating_environment = False
    try:
        if not python.is_file():
            creating_environment = True
            print(f'Creating virtual environment: {target}', flush=True)
            venv.EnvBuilder(with_pip=True).create(target)
            creating_environment = False
        run([python, '-I', '-c', 'import sys; sys.exit(0 if sys.prefix != sys.base_prefix else "Selected Python is not isolated. Choose a virtual-environment directory with --venv.")'])
        run([python, '-m', 'pip', 'install', '--upgrade', 'pip'])
        # Install the lightweight command first so the effective configuration
        # can be read correctly, including saved profiles and checkout .env.
        run([python, '-m', 'pip', 'install', '--upgrade', str(ROOT)])
        configure = [python, '-m', 'agent', 'configure', '--mode', args.mode]
        if args.overwrite_config:
            configure.append('--overwrite')
        run(configure)
        provider = configured_provider(python)
        if provider not in {'huggingface', 'ensemble', 'ollama', 'tiny', 'localserver'}:
            raise RuntimeError('Unexpected provider configuration')
        needs_hf = provider == 'huggingface' or (provider == 'ensemble' and configured_needs_hf(python))
        needs_torch = needs_hf or provider == 'tiny'
        if needs_torch and args.runtime == 'cpu':
            run([python, '-m', 'pip', 'install', 'torch>=2.6,<3', '--index-url', 'https://download.pytorch.org/whl/cpu'])
        elif provider == 'tiny':
            run([python, '-m', 'pip', 'install', 'torch>=2.6,<3'])
        if needs_hf:
            run([python, '-m', 'pip', 'install', '--upgrade', str(ROOT) + '[local]'])
        run([python, '-m', 'pip', 'check'])
        # Isolated mode verifies the installed wheel instead of a same-named
        # source tree or a package selected by an inherited PYTHONPATH.
        run([python,'-I','-m','agent','verify','--json'])
        run([python, '-m', 'agent', 'doctor'])
        if (args.download or args.launch) and needs_hf:
            print('Downloading configured model weights. The first installation can take several minutes.', flush=True)
            run([python, '-m', 'agent', 'models', 'download'])
    except KeyboardInterrupt:
        print('\nSetup interrupted. Rerun the same installer to continue.', file=sys.stderr)
        return 130
    except (subprocess.CalledProcessError, OSError, RuntimeError) as exc:
        print(f'Installation stopped: {type(exc).__name__}. Review the preceding error, fix it, and rerun the same command.', file=sys.stderr)
        if creating_environment or not python.exists():
            print('On Debian/Ubuntu, install python3-venv. On Windows, install Python 3.12 from python.org or winget.', file=sys.stderr)
        return 1
    print('\nZenith is ready. Its isolated environment is selected automatically by the launchers.')
    if target == ROOT / '.venv':
        print('Next time: double-click Start Zenith.cmd' if os.name == 'nt' else 'Next time: bash start.sh')
    prefix = '& ' if os.name == 'nt' else ''
    print(f'Browser command: {prefix}"{python}" -m agent serve --open-browser')
    if args.launch:
        print('Opening Zenith. Keep this terminal open; press Ctrl+C to stop.', flush=True)
        try:
            run([python, '-m', 'agent', 'serve', '--open-browser'])
        except KeyboardInterrupt:
            print('\nZenith stopped. Use the launcher whenever you want to return.')
        except (subprocess.CalledProcessError, OSError) as exc:
            print('Zenith was installed, but could not start. Check the error above and use the launcher to retry.', file=sys.stderr)
            return exc.returncode if isinstance(exc, subprocess.CalledProcessError) and exc.returncode > 0 else 1
    else:
        print('Use --launch with this installer to download configured HF weights and open Zenith immediately.')
    print('Advanced terminal commands: activate the environment with activate.ps1 or source ./activate.sh.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
