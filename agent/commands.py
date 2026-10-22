"""One installed command for chat, serving, diagnostics, and project utilities."""
import argparse
import importlib
import sys
from importlib.metadata import PackageNotFoundError, version

COMMANDS = {
    'chat': ('agent.cli', 'Chat in your terminal'),
    'serve': ('agent.server', 'Start browser chat on localhost'),
    'doctor': ('agent.doctor', 'Check installation and model readiness'),
    'configure': ('agent.setup', 'Save a local or Ollama configuration'),
    'models': ('agent.models', 'List, check, or download configured models'),
    'catalog': ('scripts.catalog', 'Search or validate the source catalog'),
    'import-data': ('scripts.import_dataset', 'Import selected dataset text'),
    'export-data': ('scripts.export_training_data', 'Export approved training examples'),
    'train-lora': ('scripts.train_lora', 'Train a candidate LoRA adapter'),
    'evaluate': ('scripts.evaluate', 'Evaluate a base model or adapter'),
    'train-tiny': ('scripts.train_tiny', 'Train the experimental scratch transformer'),
    'sample-tiny': ('scripts.sample_tiny', 'Generate from a scratch checkpoint'),
}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {'-h', '--help'}:
        parser = argparse.ArgumentParser(prog='zenith', description='Zenith local AI assistant. With no arguments, start terminal chat.')
        parser.add_argument('--version', action='store_true', help='Show installed version')
        sub = parser.add_subparsers(dest='command')
        for name, (_, description) in COMMANDS.items():
            sub.add_parser(name, help=description)
        parser.print_help()
        return 0
    if args == ['--version']:
        try:
            print('Zenith ' + version('zenith-local'))
        except PackageNotFoundError:
            print('Zenith (source checkout)')
        return 0
    command = args.pop(0) if args else 'chat'
    if command not in COMMANDS:
        print(f'Unknown command: {command}. Use zenith --help.', file=sys.stderr)
        return 2
    previous = sys.argv
    sys.argv = [f'zenith {command}', *args]
    try:
        result = importlib.import_module(COMMANDS[command][0]).main()
        return result if isinstance(result, int) else 0
    finally:
        sys.argv = previous


if __name__ == '__main__':
    raise SystemExit(main())
