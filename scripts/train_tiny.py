"""Train Zenith's own experimental language model from random weights."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path
from agent.paths import zenith_home


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', required=True, help='UTF-8 text you have permission to train on')
    parser.add_argument('--output-dir', default=str(zenith_home() / 'artifacts' / 'tiny'))
    parser.add_argument('--steps', type=int, default=1000)
    parser.add_argument('--context-length', type=int, default=512)
    parser.add_argument('--width', type=int, default=128)
    parser.add_argument('--layers', type=int, default=4)
    parser.add_argument('--heads', type=int, default=4)
    parser.add_argument('--batch-size', type=int, default=8)
    parser.add_argument('--learning-rate', type=float, default=3e-4)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    if args.steps < 1 or args.batch_size < 1 or args.learning_rate <= 0:
        parser.error('Steps, batch size and learning rate must be positive')
    output = Path(args.output_dir)
    if output.exists() and any(output.iterdir()):
        parser.error('Choose an empty output directory to preserve previous checkpoints')
    import torch
    from agent.tiny import TinyConfig, TinyLM, encode, save_checkpoint, EOS
    from agent.learning import file_sha256
    from agent.providers import select_device
    torch.manual_seed(args.seed)
    config = TinyConfig(context_length=args.context_length, width=args.width, layers=args.layers, heads=args.heads)
    data = torch.tensor(encode(Path(args.corpus).read_text(encoding='utf-8')) + [EOS], dtype=torch.long)
    # Contiguous split before sampling prevents overlapping train/eval windows.
    split = int(len(data) * 0.9)
    training, evaluation = data[:split], data[split:]
    if min(len(training), len(evaluation)) <= config.context_length:
        parser.error('Corpus too short for a disjoint 90/10 split. Supply more text or reduce --context-length.')
    device = select_device(torch, 'auto')
    model = TinyLM(config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    def batch(source):
        starts = torch.randint(len(source) - config.context_length, (args.batch_size,))
        x = torch.stack([source[i:i + config.context_length] for i in starts]).to(device)
        y = torch.stack([source[i + 1:i + config.context_length + 1] for i in starts]).to(device)
        return x, y
    # A fixed held-out batch makes before/after loss comparable.
    eval_x, eval_y = batch(evaluation)
    model.eval()
    with torch.no_grad():
        _, baseline = model(eval_x, eval_y)
    print(f'{sum(p.numel() for p in model.parameters()):,} parameters | {device}')
    model.train()
    for step in range(args.steps):
        x, y = batch(training)
        _, loss = model(x, y)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        if step == 0 or (step + 1) % 100 == 0 or step + 1 == args.steps:
            print(f'step={step + 1} train_loss={loss.item():.4f}')
    model.eval()
    with torch.no_grad():
        _, final = model(eval_x, eval_y)
    save_checkpoint(model, output / 'model.pt')
    report = {'config': asdict(config), 'steps': args.steps, 'seed': args.seed,
              'corpus_sha256': file_sha256(args.corpus), 'train_bytes': len(training), 'eval_bytes': len(evaluation),
              'baseline_eval_loss': baseline.item(), 'final_eval_loss': final.item(),
              'parameters': sum(p.numel() for p in model.parameters()), 'educational_model': True}
    (output / 'training_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'Saved {output}/model.pt. Experimental model: meaningful conversation needs substantial training data.')


if __name__ == '__main__':
    main()
