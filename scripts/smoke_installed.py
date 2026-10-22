"""Check installed commands from another working directory, without activation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    executable = Path(sys.executable).parent / ('zenith.exe' if os.name == 'nt' else 'zenith')
    with tempfile.TemporaryDirectory(prefix='zenith-other-directory-') as directory:
        module_path = subprocess.check_output([sys.executable, '-c', 'import agent; print(agent.__file__)'], cwd=directory, text=True, encoding='utf-8').strip()
        assert Path(module_path).resolve() != (Path(__file__).resolve().parents[1] / 'agent' / '__init__.py').resolve(), 'Smoke check must use the installed wheel, not the source checkout'
        version = subprocess.run([str(executable), '--version'], cwd=directory, text=True, encoding="utf-8",
                                 stdout=subprocess.PIPE, check=True).stdout
        assert '0.5.0' in version
        resources = subprocess.check_output([sys.executable, '-c',
            'from pathlib import Path; import agent; from agent.packs import summaries; '
            'assert len(summaries()) == 3; '
            'assert (Path(agent.__file__).parent / "web" / "zenith-banner.png").is_file()'],
            cwd=directory, text=True, encoding='utf-8')
        report = subprocess.run([str(executable), 'doctor', '--json'], cwd=directory, text=True, encoding="utf-8",
                                stdout=subprocess.PIPE, check=True).stdout
        result = json.loads(report)
        assert result['ok']
        catalog = subprocess.run([str(executable), 'catalog', '--validate'], cwd=directory,
                                 text=True, encoding="utf-8", stdout=subprocess.PIPE, check=True).stdout
        assert json.loads(catalog)['counts']['models'] == 1000
        chat = subprocess.run([str(executable), 'chat'], input='/quit\n', cwd=directory,
                              text=True, encoding="utf-8", stdout=subprocess.PIPE, check=True).stdout
        assert 'Goodbye.' in chat
    print('Installed command, catalog, diagnostics and terminal exit work outside the checkout.')


if __name__ == '__main__':
    main()
