"""One installed command for chat, serving, diagnostics, and project utilities."""
import argparse
import importlib
import sys
from . import __version__

COMMANDS = {
    'analyze': ('agent.data_analysis', 'Summarize a bounded UTF-8 CSV locally with verified decimal arithmetic'),
    'reason': ('agent.reasoning', 'Run bounded native reasoning with optional exact arithmetic checks'),
    'model-registry': ('agent.model_registry', 'Inspect runtime models or explicitly discover account-visible provider IDs'),
    'route': ('agent.orchestration', 'Run native Zenith or explicitly configured hybrid inference'),
    'chat': ('agent.cli', 'Chat in your terminal'),
    'serve': ('agent.server', 'Start browser chat on localhost'),
    'doctor': ('agent.doctor', 'Check installation and model readiness'),
    'verify': ('agent.integrity', 'Verify installed files or a complete source release manifest'),
    'configure': ('agent.setup', 'Save a local or Ollama configuration'),
    'setup': ('agent.setup', 'Configure Zenith or explicitly activate its experimental candidate'),
    'models': ('agent.models', 'List, check, or download configured models'),
    'packs': ('agent.packs', 'Inspect, verify, download or configure Zenith model packs'),
    'skills': ('agent.skills', 'Browse AI/security learning profiles, workflows, and reference resources'),
    'admin': ('agent.admin', 'Configure your local owner code without exposing it in chat'),
    'benchmark': ('agent.quality', 'Run versioned task/slice evaluations and latency comparisons'),
    'curriculum': ('agent.curriculum', 'Prepare and audit versioned training/validation/test data'),
    'import-book': ('agent.books', 'Snapshot a public-domain book for source-linked local retrieval'),
    'checkpoint': ('agent.checkpoints', 'Verify an existing trained Zenith adapter and its original tokenizer'),
    'continuation-campaign': ('scripts.run_continuation_campaign', 'Run a checkpoint-preserving candidate and prepare its review evidence'),
    'continue-training': ('agent.continual', 'Continue a verified trained checkpoint into a separate unpromoted candidate'),
    'export-checkpoint': ('agent.export_checkpoint', 'Merge and reload an existing adapter locally; never publish or promote'),
    'stabilize-checkpoint': ('agent.stabilize', 'Average same-lineage adapter versions into a separate, unpromoted experiment'),
    'expansion-eval': ('agent.expansion_eval', 'Measure raw-model domain diagnostics without harness shortcuts'),
    'deployment': ('agent.deployment', 'Review measured candidates, explicitly activate a local profile, or roll back'),
    'campaign': ('scripts.run_training_campaign', 'Run a bounded training candidate with held-out and regression reports'),
    'system': ('agent.monitoring', 'Inspect the five system components or local performance aggregates'),
    'discover': ('agent.discovery', 'Discover public models, including fine-tunes, and save model references'),
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
        print('Zenith ' + __version__)
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
