"""Continue an existing trained Zenith adapter; candidates never auto-deploy."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import random
import time
from uuid import uuid4
from .checkpoints import load_existing, inventory, digest, tokenizer_signature
from .learning import load_examples, prepare_chat_example


def sequence_logprob(model, item):
    import torch
    ids=torch.tensor([item['input_ids']],device=next(model.parameters()).device)
    labels=torch.tensor([item['labels']],device=ids.device)
    output=model(input_ids=ids,attention_mask=torch.ones_like(ids)).logits[:,:-1].float()
    targets=labels[:,1:]
    mask=targets.ne(-100)
    safe=targets.masked_fill(~mask,0)
    selected=output.log_softmax(-1).gather(-1,safe.unsqueeze(-1)).squeeze(-1)
    return (selected*mask).sum(),mask.sum()


def prepare_record(tokenizer,row,max_length,objective):
    from .curriculum import SECRET_PATTERN
    if objective=='cpt':
        text=row.get('text')
        if not isinstance(text,str) or not text.strip() or len(text)>24000 or SECRET_PATTERN.search(text):
            raise ValueError('Continued-pretraining rows require reviewed text')
        ids=tokenizer.encode(text,add_special_tokens=False)+[tokenizer.eos_token_id]
        if len(ids)>max_length or len(ids)<2:return None
        return {'input_ids':ids,'labels':ids}
    if objective=='dpo':
        if row.get('preference_validated') is not True:raise ValueError('Preference pairs require explicit validation')
        if not all(isinstance(row.get(k),str) and row[k].strip() for k in ['chosen','rejected']):
            raise ValueError('Preference rows require validated chosen and rejected responses')
        if row['chosen']==row['rejected'] or any(len(row[k])>24000 or SECRET_PATTERN.search(row[k]) for k in ['chosen','rejected']):
            raise ValueError('Preference pair is identical, oversized, or contains a credential')
        context=row['messages'][:-1]
        chosen=prepare_chat_example(tokenizer,context+[{'role':'assistant','content':row['chosen']}],max_length)
        rejected=prepare_chat_example(tokenizer,context+[{'role':'assistant','content':row['rejected']}],max_length)
        if chosen is None or rejected is None:return None
        return {'chosen':chosen,'rejected':rejected}
    return prepare_chat_example(tokenizer,row['messages'],max_length)


def mean_loss(model,items,objective):
    import torch
    model.eval();losses=[]
    with torch.inference_mode():
        for item in items:
            value=item['chosen'] if objective=='dpo' else item
            lp,count=sequence_logprob(model,value)
            losses.append(float(-lp/count))
    return sum(losses)/len(losses)


def continue_training(parent,dataset,output,steps=40,max_length=256,learning_rate=2e-5,objective='sft',seed=42,replay_fraction=0.25,start_offset=0,device='auto'):
    if type(start_offset)!=int or not 0<=start_offset<=1000000:raise ValueError('Invalid curriculum schedule offset')
    if objective not in {'sft','cpt','dpo'} or not 1<=steps<=5000 or not 32<=max_length<=32768 or not 0<learning_rate<=0.01 or not 0<=replay_fraction<=0.9:
        raise ValueError('Invalid continuation objective or resource limits')
    from .curriculum import audit_directory,assert_disjoint
    manifest=audit_directory(dataset)
    partitions={name:load_examples(Path(dataset)/manifest['files'][name]['path']) for name in ['train','validation','test']}
    assert_disjoint(partitions)
    from .curriculum import validate_rows
    for rows in partitions.values():validate_rows(rows)
    if any(row.get('retention_replay') for name in ['validation','test'] for row in partitions[name]):
        raise ValueError('Historical replay is forbidden in held-out partitions')
    if manifest.get('replay'):
        replay_info=manifest['replay']
        replay_path=(Path(dataset)/replay_info['path']).resolve()
        if replay_path.parent!=Path(dataset).resolve() or digest(replay_path)!=replay_info['snapshot_sha256']:
            raise ValueError('Historical replay snapshot was changed')
        from .curriculum import row_keys
        replay_keys=set().union(*(row_keys(row) for row in load_examples(replay_path)))
        if any(row_keys(row)&replay_keys for name in ['validation','test'] for row in partitions[name]):
            raise ValueError('Held-out data overlaps historical replay')
    root=Path(output).expanduser().resolve()
    parent=Path(parent).expanduser().resolve()
    if root==parent or parent in root.parents or root in parent.parents or root.exists():
        raise ValueError('Choose a new candidate directory outside the original checkpoint')
    import torch
    from transformers import set_seed
    set_seed(seed)
    model,tokenizer,details=load_existing(parent,trainable=True)
    if device not in {'auto','cpu','cuda'}:raise ValueError('Choose auto, cpu, or cuda')
    selected_device='cuda' if device=='auto' and torch.cuda.is_available() else ('cpu' if device=='auto' else device)
    if selected_device=='cuda' and not torch.cuda.is_available():raise ValueError('CUDA is unavailable; choose CPU or provide a supported GPU')
    model.to(selected_device)
    if selected_device=='cuda':torch.cuda.reset_peak_memory_stats()
    if max_length>details['context_limit']:
        raise ValueError('Requested training context exceeds the unchanged architecture limit')
    prepared={}
    for name,rows in partitions.items():
        if name=='test':continue
        pairs=[(row,prepare_record(tokenizer,row,max_length,objective)) for row in rows]
        prepared[name]=[(row,item) for row,item in pairs if item is not None]
        if not prepared[name]:raise ValueError('No usable '+name+' records; revise data or context limit')
    training=prepared['train'];validation=[item for _,item in prepared['validation']]
    replay=[pair for pair in training if pair[0].get('retention_replay')]
    new=[pair for pair in training if not pair[0].get('retention_replay')]
    if replay_fraction and not replay:
        raise ValueError('Continual learning requires explicit previous-domain replay records')
    if not new:raise ValueError('No new-domain training records')
    randomizer=random.Random(seed);randomizer.shuffle(replay);randomizer.shuffle(new)
    reference={}
    model.config.use_cache=False
    if objective=='dpo':
        model.eval()
        with torch.inference_mode():
            for row,item in training:
                reference[row['id']]=float(sequence_logprob(model,item['chosen'])[0]-sequence_logprob(model,item['rejected'])[0])
    baseline=mean_loss(model,validation,objective)
    parameters=[p for p in model.parameters() if p.requires_grad]
    if not parameters or any(p.requires_grad for name,p in model.named_parameters() if 'lora_' not in name):
        raise ValueError('Unexpected trainable parameters; refusing to modify the original base weights')
    optimizer=torch.optim.AdamW(parameters,lr=learning_rate)
    root.mkdir(parents=True,exist_ok=False)
    if selected_device=='cuda':torch.cuda.synchronize()
    started=time.perf_counter();losses=[];input_tokens=target_tokens=0;coverage=Counter();used=[]
    for local_step in range(steps):
        step=local_step+start_offset
        # Deterministic interleaving avoids dropping retained domains in a short run.
        replay_due=bool(replay) and math.floor((step+1)*replay_fraction)>math.floor(step*replay_fraction)
        pool=replay if replay_due else new
        index=math.floor(step*replay_fraction) if replay_due else step-math.floor(step*replay_fraction)
        row,item=pool[index%len(pool)]
        model.train();optimizer.zero_grad(set_to_none=True)
        if objective=='dpo':
            model.eval()
            good,good_n=sequence_logprob(model,item['chosen'])
            bad,bad_n=sequence_logprob(model,item['rejected'])
            loss=-torch.nn.functional.logsigmoid(0.1*(good-bad-reference[row['id']]))
            input_tokens+=len(item['chosen']['input_ids'])+len(item['rejected']['input_ids'])
            target_tokens+=int(good_n+bad_n)
        else:
            lp,count=sequence_logprob(model,item)
            loss=-lp/count
            input_tokens+=len(item['input_ids']);target_tokens+=int(count)
        if not bool(torch.isfinite(loss)):raise ValueError('Non-finite training loss; candidate remains incomplete')
        loss.backward();torch.nn.utils.clip_grad_norm_(parameters,1.0);optimizer.step()
        losses.append(float(loss.detach()));coverage[row['topic']]+=1;used.append(row['id'])
        print(json.dumps({'step':local_step+1,'steps':steps,'curriculum_step':step+1,'loss':losses[-1],'topic':row['topic']}),flush=True)
    if selected_device=='cuda':torch.cuda.synchronize()
    seconds=time.perf_counter()-started
    final=mean_loss(model,validation,objective)
    if inventory(details['base_snapshot'])!=details['base_files']:
        raise ValueError('Original base snapshot changed during training')
    if inventory(parent)!=details['parent_files']:
        raise ValueError('Parent files changed during training; candidate cannot be accepted')
    if tokenizer_signature(tokenizer)!=details['tokenizer_sha256']:
        raise ValueError('Tokenizer changed; export refused')
    model.save_pretrained(root,safe_serialization=True);tokenizer.save_pretrained(root)
    report={'schema_version':1,'run_id':datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:8],
        'base_model':details['base_model'],'base_revision':details['base_revision'],
        'parent':str(parent),'parent_files':details['parent_files'],'parent_training_report_sha256':digest(parent/'training_report.json'),
        'tokenizer_sha256':details['tokenizer_sha256'],'architecture':details,
        'objective':objective,'seed':seed,'start_offset':start_offset,'optimizer_state_resumed':False,'learning_rate':learning_rate,'max_length':max_length,'replay_fraction':replay_fraction,
        'train_examples':len(training),'eval_examples':len(validation),'dataset_manifest_sha256':digest(Path(dataset)/'manifest.json'),
        'dataset_files':manifest['files'],'skipped':{name:len(partitions[name])-len(prepared[name]) for name in prepared},
        'baseline':{'validation_target_loss':baseline},'final':{'validation_target_loss':final},
        'training':{'train_loss':sum(losses)/len(losses),'train_runtime':seconds,'optimizer_steps':steps,
            'input_tokens_seen':input_tokens,'target_tokens_seen':target_tokens,'tokens_per_second':input_tokens/seconds,
            'topics_seen':dict(coverage),'unique_training_records_seen':len(set(used)),'record_ids_seen':used,
            'replay_steps':sum(1 for i in range(start_offset,start_offset+steps) if math.floor((i+1)*replay_fraction)>math.floor(i*replay_fraction)),
            'gpu_utilization':None,'gpu_utilization_reason':'CPU experiment' if selected_device=='cpu' else 'GPU utilization percentage was not sampled',
            'gpu_peak_allocated_bytes':torch.cuda.max_memory_allocated() if selected_device=='cuda' else None,
            'device':str(next(model.parameters()).device)},
        'original_checkpoints_modified':False,'weights_reinitialized':False,'automatic_promotion':False,'promoted':False,
        'final_test_used_for_training':False,'evaluation_pending':True}
    with (root/'training_report.json').open('x',encoding='utf-8') as handle:json.dump(report,handle,indent=2)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent',type=Path,required=True)
    parser.add_argument('--dataset',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--steps',type=int,default=40)
    parser.add_argument('--max-length',type=int,default=256)
    parser.add_argument('--learning-rate',type=float,default=2e-5)
    parser.add_argument('--device',choices=['auto','cpu','cuda'],default='auto')
    parser.add_argument('--start-offset',type=int,default=0,help='Continue a deterministic curriculum schedule; optimizer state is reset explicitly')
    parser.add_argument('--replay-fraction',type=float,default=0.25,help='Fraction of optimizer steps using historical training-only replay')
    parser.add_argument('--objective',choices=['sft','cpt','dpo'],default='sft')
    args=parser.parse_args()
    try:report=continue_training(args.parent,args.dataset,args.output,args.steps,args.max_length,args.learning_rate,args.objective,replay_fraction=args.replay_fraction,start_offset=args.start_offset,device=args.device)
    except (ValueError,OSError) as exc:parser.error(str(exc))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
