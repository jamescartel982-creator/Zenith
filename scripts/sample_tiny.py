"""Generate text from a Zenith Tiny checkpoint."""
import argparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', default='artifacts/tiny/model.pt')
    parser.add_argument('--prompt', default='User: Hello\nAssistant:')
    parser.add_argument('--max-new-tokens', type=int, default=128)
    parser.add_argument('--temperature', type=float, default=0.7)
    args = parser.parse_args()
    if not args.prompt or not 1 <= args.max_new_tokens <= 4096 or not 0 <= args.temperature <= 2:
        parser.error('Use a nonempty prompt, 1–4096 tokens, and temperature 0–2')
    import torch
    from agent.tiny import load_checkpoint, encode, decode
    from agent.providers import select_device
    device = select_device(torch, 'auto')
    model = load_checkpoint(args.checkpoint, device)
    ids = torch.tensor([encode(args.prompt)], device=device)
    output = model.generate(ids, args.max_new_tokens, args.temperature)
    print(decode(output[0].tolist()))


if __name__ == '__main__':
    main()
