"""Local merge/export with logit equivalence and tokenizer verification."""
import argparse
import json
from pathlib import Path
from .checkpoints import load_existing,inventory,tokenizer_signature


def merge_export(parent,output):
    import torch
    from transformers import AutoModelForCausalLM
    from .tokenization import load_preserved_tokenizer
    parent=Path(parent).resolve();output=Path(output).resolve()
    if output.exists() or parent==output or parent in output.parents or output in parent.parents:
        raise ValueError('Export requires a new directory separate from every source checkpoint')
    model,tokenizer,details=load_existing(parent)
    ids=tokenizer('Zenith export compatibility check: 2 + 2 =',return_tensors='pt')['input_ids']
    with torch.inference_mode():before=model(ids).logits[:,-1].float()
    merged=model.merge_and_unload(safe_merge=True)
    with torch.inference_mode():after=merged(ids).logits[:,-1].float()
    error=float((before-after).abs().max())
    if not torch.allclose(before,after,atol=1e-4,rtol=1e-4):
        raise ValueError('Merged logits differ from the adapter model beyond tolerance')
    output.mkdir(parents=True,exist_ok=False)
    merged.save_pretrained(output,safe_serialization=True,max_shard_size='1GB')
    tokenizer.save_pretrained(output)
    del model,merged
    import gc;gc.collect()
    reloaded,loading=AutoModelForCausalLM.from_pretrained(output,local_files_only=True,trust_remote_code=False,use_safetensors=True,dtype=torch.float32,output_loading_info=True)
    if any(loading.get(k) for k in ['missing_keys','unexpected_keys','mismatched_keys','error_msgs']):
        raise ValueError('Export reload did not load exact trained weights')
    reloaded.eval()
    actual_tokenizer=load_preserved_tokenizer(output,local_files_only=True)
    if tokenizer_signature(actual_tokenizer)!=details['tokenizer_sha256']:
        raise ValueError('Export tokenizer is incompatible')
    with torch.inference_mode():actual=reloaded(ids).logits[:,-1].float()
    if not torch.allclose(after,actual,atol=1e-4,rtol=1e-4):raise ValueError('Saved export does not match merged inference')
    if inventory(parent)!=details['parent_files']:raise ValueError('Original checkpoint was modified')
    report={'schema_version':1,'parent':str(parent),'parent_files':details['parent_files'],
        'base_model':details['base_model'],'base_revision':details['base_revision'],
        'architecture_unchanged':True,'tokenizer_sha256':details['tokenizer_sha256'],
        'maximum_merge_logit_error':error,'merge_and_reload_verified':True,
        'export_files':inventory(output),'export_bytes':sum(p.stat().st_size for p in output.rglob('*') if p.is_file()),
        'published':False,'deployment_approved':False,'automatic_promotion':False,
        'notice':'Local compatibility export only. Passing these checks does not approve benchmark quality or deployment.'}
    (output/'export_report.json').write_text(json.dumps(report,indent=2))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:result=merge_export(args.parent,args.output)
    except (ValueError,OSError) as exc:parser.error(str(exc))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
