"""Evaluate base or adapter loss using the same final-answer masking as training."""
import argparse
import json
from agent.learning import load_examples, prepare_chat_example, ChatCollator


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-model', default='Qwen/Qwen2.5-0.5B-Instruct')
    parser.add_argument('--revision', default='main')
    parser.add_argument('--adapter', default=None)
    parser.add_argument('--data', default='data/eval.jsonl')
    parser.add_argument('--max-length', type=int, default=1024)
    args = parser.parse_args()
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from agent.providers import select_device
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, revision=args.revision, trust_remote_code=False)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.base_model, revision=args.revision, trust_remote_code=False,
                                               use_safetensors=True, dtype=torch.float32)
    if args.adapter:
        from peft import PeftModel, PeftConfig
        if PeftConfig.from_pretrained(args.adapter).base_model_name_or_path != args.base_model:
            parser.error('Adapter base model does not match --base-model')
        model = PeftModel.from_pretrained(model, args.adapter)
    model.to(select_device(torch, 'auto')).eval()
    collator = ChatCollator(tokenizer.pad_token_id)
    loss_sum, targets, skipped, count = 0.0, 0, 0, 0
    with torch.inference_mode():
        for row in load_examples(args.data):
            example = prepare_chat_example(tokenizer, row['messages'], args.max_length)
            if example is None:
                skipped += 1
                continue
            batch = {k: v.to(model.device) for k, v in collator([example]).items()}
            target_count = int((batch['labels'][:, 1:] != -100).sum())
            loss_sum += model(**batch).loss.item() * target_count
            targets += target_count
            count += 1
    if targets == 0:
        parser.error('No usable evaluation targets')
    print(json.dumps({'base_model': args.base_model, 'adapter': args.adapter, 'examples': count,
                      'skipped': skipped, 'target_tokens': targets, 'mean_target_loss': loss_sum / targets}, indent=2))


if __name__ == '__main__':
    main()
