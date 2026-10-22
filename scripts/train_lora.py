"""Fine-tune a chat model with LoRA and evaluate before/after on held-out data."""
import argparse
import json
from pathlib import Path
from agent.config import Settings
from agent.paths import zenith_home
from agent.learning import load_examples, prepare_chat_example, ChatCollator, file_sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-model', default='Qwen/Qwen2.5-0.5B-Instruct')
    parser.add_argument('--revision', default='main')
    parser.add_argument('--train-data', default=str(Path(Settings().data_dir) / 'training.jsonl'))
    parser.add_argument('--eval-data', default=str(Path(Settings().data_dir) / 'eval.jsonl'))
    parser.add_argument('--output-dir', default=str(zenith_home() / 'artifacts' / 'zenith-lora'))
    parser.add_argument('--epochs', type=float, default=1.0)
    parser.add_argument('--max-steps', type=int, default=-1, help='Optional bounded smoke run')
    parser.add_argument('--max-length', type=int, default=1024)
    parser.add_argument('--batch-size', type=int, default=1)
    parser.add_argument('--gradient-accumulation', type=int, default=4)
    parser.add_argument('--learning-rate', type=float, default=2e-4)
    parser.add_argument('--dataset-manifest', type=Path, help='Audit the immutable curriculum manifest and final-test isolation')
    parser.add_argument('--cpu-threads',type=int,default=Settings().cpu_threads)
    args = parser.parse_args()
    if args.max_length < 16 or args.epochs <= 0 or args.batch_size < 1 or args.gradient_accumulation < 1 or args.learning_rate <= 0 or args.max_steps == 0 or args.max_steps < -1 or not 1<=args.cpu_threads<=64:
        parser.error('Invalid training limits')
    output = Path(args.output_dir)
    if output.exists() and any(output.iterdir()):
        parser.error('Output directory must be empty; preserve existing adapters for rollback')
    for path in (args.train_data, args.eval_data):
        if not Path(path).is_file():
            parser.error(f'Missing {path}. Export approved examples first.')
    train_rows, eval_rows = load_examples(args.train_data), load_examples(args.eval_data)
    test_sha256=None
    if args.dataset_manifest:
        from agent.curriculum import audit_directory,assert_disjoint
        try:
            manifest=audit_directory(args.dataset_manifest.parent)
            for partition,given in [('train',args.train_data),('validation',args.eval_data)]:
                if Path(given).resolve()!=(args.dataset_manifest.parent/manifest['files'][partition]['path']).resolve():
                    raise ValueError('Training arguments do not match the versioned train/validation files')
            test_path=args.dataset_manifest.parent/manifest['files']['test']['path']
            assert_disjoint({'train':train_rows,'validation':eval_rows,'test':load_examples(test_path)})
            test_sha256=file_sha256(test_path)
        except (ValueError,OSError,KeyError) as exc:parser.error(str(exc))
    def prompts(rows):
        return {' '.join((row.get('prompt') or row['messages'][-2]['content']).casefold().split()) for row in rows}
    if prompts(train_rows) & prompts(eval_rows):
        parser.error('Train/eval contain repeated prompts. Re-export with grouped splitting.')
    train_sessions = {row['conversation_id'] for row in train_rows if row.get('conversation_id')}
    eval_sessions = {row['conversation_id'] for row in eval_rows if row.get('conversation_id')}
    if train_sessions & eval_sessions:
        parser.error('Train/eval share conversations; re-export to avoid context leakage.')
    if len(train_rows) < 5 or not eval_rows:
        parser.error('Need at least five training examples and one held-out evaluation example')

    import torch
    torch.set_num_threads(args.cpu_threads)
    from datasets import Dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments, set_seed
    from peft import LoraConfig, TaskType, get_peft_model
    set_seed(42)
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, revision=args.revision, trust_remote_code=False)
    if not tokenizer.chat_template:
        parser.error('Choose an instruction/chat model with a chat template')
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    def prepare(rows):
        items = [prepare_chat_example(tokenizer, row['messages'], args.max_length) for row in rows]
        return [item for item in items if item is not None]
    train, evaluation = prepare(train_rows), prepare(eval_rows)
    skipped = {'train': len(train_rows) - len(train), 'eval': len(eval_rows) - len(evaluation)}
    print(f'Examples over the length limit or without targets skipped: {skipped}')
    if len(train) < 5 or not evaluation:
        parser.error('Too few usable examples; collect more or increase --max-length')
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model, revision=args.revision, trust_remote_code=False,
        use_safetensors=True, dtype=torch.float32)
    if args.max_length > getattr(model.config, 'max_position_embeddings', args.max_length):
        parser.error('--max-length exceeds the model context window')
    resolved_revision = getattr(model.config, '_commit_hash', args.revision)
    model.config.use_cache = False
    model = get_peft_model(model, LoraConfig(
        task_type=TaskType.CAUSAL_LM, r=8, lora_alpha=16,
        lora_dropout=0.05, target_modules='all-linear'))
    model.print_trainable_parameters()
    training_args = TrainingArguments(
        output_dir=str(output), num_train_epochs=args.epochs, max_steps=args.max_steps,
        per_device_train_batch_size=args.batch_size, per_device_eval_batch_size=1,
        gradient_accumulation_steps=args.gradient_accumulation,
        learning_rate=args.learning_rate, save_strategy='no', logging_steps=1,
        report_to='none', seed=42, dataloader_pin_memory=torch.cuda.is_available(),
    )
    trainer = Trainer(model=model, args=training_args, train_dataset=Dataset.from_list(train),
                      eval_dataset=Dataset.from_list(evaluation), data_collator=ChatCollator(tokenizer.pad_token_id))
    baseline = trainer.evaluate()
    trained = trainer.train()
    final = trainer.evaluate()
    model.save_pretrained(output, safe_serialization=True)
    tokenizer.save_pretrained(output)
    manifest = {
        'base_model': args.base_model, 'base_revision': resolved_revision,
        'train_sha256': file_sha256(args.train_data), 'eval_sha256': file_sha256(args.eval_data),
        'train_examples': len(train), 'eval_examples': len(evaluation), 'skipped': skipped,
        'baseline': baseline, 'final': final, 'training': trained.metrics,
        'parameters': vars(args), 'automatic_promotion': False,
        'final_test_sha256':test_sha256,'final_test_used_for_training':False,
    }
    (output / 'training_report.json').write_text(json.dumps(manifest, indent=2,default=str), encoding='utf-8')
    print(f'Saved adapter and training_report.json in {output}.')
    print('Compare held-out results and chat quality before selecting ZENITH_ADAPTER. Improvement is not guaranteed.')


if __name__ == '__main__':
    main()
