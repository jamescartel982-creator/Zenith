"""Export approved current reviews, preserving the actual conversation input."""
import argparse
import json
from pathlib import Path
from agent.config import Settings
from agent.storage import Store
from agent.learning import split_examples, write_jsonl, file_sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', default=Settings().data_dir)
    parser.add_argument('--output-dir', default=None)
    parser.add_argument('--eval-fraction', type=float, default=0.2)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    examples = Store(args.data_dir).approved_examples()
    train, evaluation = split_examples(examples, args.eval_fraction, args.seed)
    output = Path(args.output_dir or args.data_dir)
    write_jsonl(output / 'training.jsonl', train)
    write_jsonl(output / 'eval.jsonl', evaluation)
    manifest = {'approved_turns': len(examples), 'train_examples': len(train), 'eval_examples': len(evaluation),
                'seed': args.seed, 'training_sha256': file_sha256(output / 'training.jsonl'),
                'eval_sha256': file_sha256(output / 'eval.jsonl')}
    (output / 'dataset_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))
    print(f'Wrote {output}/training.jsonl and eval.jsonl. Review both before training.')
    if not evaluation:
        print('Need at least two independent approved conversations without repeated prompts to create a held-out split.')


if __name__ == '__main__':
    main()
