"""Inspect and load existing trained checkpoints without creating a new model."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import time


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def inventory(directory):
    root = Path(directory).resolve()
    names = sorted(p for p in root.rglob('*') if p.is_file() and '.git' not in p.parts)
    if not names:
        raise ValueError('Checkpoint directory is empty')
    return {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size, 'sha256': digest(p)} for p in names}


def tokenizer_signature(tokenizer):
    special_tokens = dict(tokenizer.special_tokens_map)
    # Transformers 5 renamed this public attribute and omits it from the map.
    # Canonicalize its name, retaining every value in the original fingerprint.
    extra = getattr(tokenizer, 'extra_special_tokens', None)
    if 'additional_special_tokens' not in special_tokens and isinstance(extra, list) and extra:
        special_tokens['additional_special_tokens'] = extra
    value = {'backend': json.loads(tokenizer.backend_tokenizer.to_str()),
             'chat_template': tokenizer.chat_template, 'special_tokens': special_tokens,
             'bos':tokenizer.bos_token_id,'eos':tokenizer.eos_token_id,'pad':tokenizer.pad_token_id}
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def parent_metadata(directory):
    root = Path(directory).expanduser().resolve()
    for name in ['adapter_config.json','adapter_model.safetensors','tokenizer.json','training_report.json']:
        if not (root / name).is_file():
            raise ValueError('Existing trained adapter is missing ' + name)
    config = json.loads((root/'adapter_config.json').read_text())
    report = json.loads((root/'training_report.json').read_text())
    base = report.get('base_model')
    revision = report.get('base_revision')
    if not base or config.get('base_model_name_or_path') != base or not re.fullmatch(r'[a-f0-9]{40}',revision or ''):
        raise ValueError('Parent checkpoint needs a consistent base identity and pinned commit revision')
    history = report.get('training',{})
    if not math.isfinite(history.get('train_loss',float('nan'))) or history.get('train_runtime',0) <= 0 or report.get('train_examples',0) < 1:
        raise ValueError('Parent checkpoint has no usable completed-training evidence')
    if config.get('peft_type') != 'LORA' or config.get('task_type') != 'CAUSAL_LM':
        raise ValueError('This continuation workflow requires an existing causal-LM LoRA checkpoint')
    from safetensors import safe_open
    nonzero = False
    with safe_open(root/'adapter_model.safetensors',framework='pt',device='cpu') as tensors:
        for key in tensors.keys():
            tensor = tensors.get_tensor(key)
            if not tensor.isfinite().all():
                raise ValueError('Parent adapter contains non-finite weights')
            if 'lora_B' in key and bool(tensor.count_nonzero()):
                nonzero = True
    if not nonzero:
        raise ValueError('Parent LoRA has no learned nonzero B weights; refusing an untrained adapter')
    return root, config, report


def load_existing(directory, trainable=False, cpu_threads=2):
    """Keep the parent's base, architecture, vocabulary and learned LoRA values."""
    import torch
    from transformers import AutoModelForCausalLM
    from .tokenization import load_preserved_tokenizer
    from peft import PeftModel
    torch.set_num_threads(cpu_threads)
    root, adapter_config, report = parent_metadata(directory)
    base, revision = report['base_model'],report['base_revision']
    from huggingface_hub import snapshot_download
    from .models import WEIGHT_PATTERNS
    snapshot=Path(snapshot_download(repo_id=base,revision=revision,local_files_only=True,allow_patterns=WEIGHT_PATTERNS))
    base_files=inventory(snapshot)
    weight=(snapshot/'model.safetensors').resolve()
    if weight.is_file() and re.fullmatch(r'[a-f0-9]{64}',weight.name) and digest(weight)!=weight.name:
        raise ValueError('Cached base weights do not match their content-addressed blob hash')
    tokenizer = load_preserved_tokenizer(base,revision=revision,local_files_only=True)
    parent_tokenizer = load_preserved_tokenizer(root,local_files_only=True)
    if tokenizer_signature(tokenizer) != tokenizer_signature(parent_tokenizer):
        raise ValueError('Parent and base tokenizer definitions differ; explicit compatibility review is required')
    model, loading = AutoModelForCausalLM.from_pretrained(base,revision=revision,trust_remote_code=False,
        local_files_only=True,use_safetensors=True,dtype=torch.float32,output_loading_info=True)
    if any(loading.get(key) for key in ['missing_keys','unexpected_keys','mismatched_keys','error_msgs']):
        raise ValueError('Base checkpoint did not load exactly; random replacement weights are forbidden')
    if len(tokenizer) > model.get_input_embeddings().weight.shape[0]:
        raise ValueError('Tokenizer exceeds the existing embedding vocabulary')
    base_parameters = sum(p.numel() for p in model.parameters())
    config = model.config.to_dict()
    model = PeftModel.from_pretrained(model,root,is_trainable=trainable)
    if not all(bool(p.isfinite().all()) for p in model.parameters()):
        raise ValueError('Loaded checkpoint contains non-finite parameters')
    model.eval()
    details = {'base_model':base,'base_revision':revision,'architecture':config.get('architectures'),
        'model_type':config.get('model_type'),'base_parameters':base_parameters,'base_files':base_files,'base_snapshot':str(snapshot),
        'total_parameters_with_adapter':sum(p.numel() for p in model.parameters()),
        'trainable_parameters':sum(p.numel() for p in model.parameters() if p.requires_grad),
        'layers':config.get('num_hidden_layers'),'hidden_size':config.get('hidden_size'),
        'attention_heads':config.get('num_attention_heads'),'kv_heads':config.get('num_key_value_heads'),
        'context_limit':config.get('max_position_embeddings'),'embedding_vocabulary':config.get('vocab_size'),
        'tokenizer_size':len(tokenizer),'tokenizer_sha256':tokenizer_signature(tokenizer),
        'checkpoint_format':'PEFT LoRA safetensors plus original pinned base safetensors',
        'framework':{'torch':torch.__version__,'transformers':__import__('transformers').__version__,'peft':__import__('peft').__version__},
        'parent':str(root),'parent_files':inventory(root),'training_history':report,
        'original_checkpoints_modified':False,'random_initialization_used':False,
        'hardware':{'device':'cpu','cuda_available':torch.cuda.is_available(),'cpu_threads':cpu_threads}}
    return model,tokenizer,details


def inspect_checkpoint(directory, output=None):
    import torch
    started=time.perf_counter()
    model,tokenizer,report=load_existing(directory)
    tokens=tokenizer.apply_chat_template([{'role':'user','content':'What is 2 plus 2? Answer briefly.'}],tokenize=True, return_dict=False,add_generation_prompt=True,return_tensors='pt')
    with torch.inference_mode():
        result=model.generate(tokens,attention_mask=torch.ones_like(tokens),max_new_tokens=32,do_sample=False,pad_token_id=tokenizer.eos_token_id)
    report.update(loaded_successfully=True,inference=tokenizer.decode(result[0,tokens.shape[1]:],skip_special_tokens=True),inspection_seconds=time.perf_counter()-started)
    if output:
        path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x',encoding='utf-8') as handle:json.dump(report,handle,indent=2)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        report=inspect_checkpoint(args.parent,args.output)
    except (ValueError,OSError) as exc:parser.error(str(exc))
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
