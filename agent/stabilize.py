"""Average adjacent trained versions of the same adapter without changing rank.

This is a weight-space stability experiment, not additional gradient training.
All historical training metrics retain their original scope.
"""
import argparse
import json
from pathlib import Path
import shutil
import time
from .checkpoints import parent_metadata,inventory,digest


def stabilize(parent,references,output):
    root,config,history=parent_metadata(parent);references=[Path(p).resolve() for p in references]
    output=Path(output).expanduser().resolve()
    sources=[root,*references]
    if len(sources)!=len(set(sources)) or not 2<=len(sources)<=6:raise ValueError('Choose two to six distinct same-lineage checkpoints')
    if output.exists() or any(output==p or p in output.parents or output in p.parents for p in sources):
        raise ValueError('Use a new output directory separate from all original checkpoints')
    # Every reference must be an actual ancestor of the latest trained parent.
    ancestors={};cursor=history
    for _ in range(100):
        prior=cursor.get('parent')
        if not prior:break
        path=Path(prior).resolve()
        if path in ancestors:raise ValueError('Training lineage contains a cycle')
        if inventory(path)!=cursor.get('parent_files'):raise ValueError('An original ancestor checkpoint changed')
        ancestors[path]=True;cursor=json.loads((path/'training_report.json').read_text())
    if any(p not in ancestors for p in references):raise ValueError('A reference is not an ancestor of this trained model')
    snapshots={str(p):inventory(p) for p in sources}
    def normalized(value):
        result=dict(value)
        for key in ['target_modules','exclude_modules','modules_to_save']:
            if isinstance(result.get(key),list):result[key]=sorted(result[key])
        return result
    for path in references:
        _,other,report=parent_metadata(path)
        if normalized(other)!=normalized(config) or (report['base_model'],report['base_revision'],report.get('tokenizer_sha256'))!=(history['base_model'],history['base_revision'],history.get('tokenizer_sha256')):
            raise ValueError('Adapter architecture, base, or tokenizer differs')
    from safetensors.torch import load_file,save_file
    import torch
    torch.set_num_threads(2)
    started=time.perf_counter();weights=load_file(str(root/'adapter_model.safetensors'));keys=set(weights)
    weights={key:value.float()/len(sources) for key,value in weights.items()}
    for path in references:
        incoming=load_file(str(path/'adapter_model.safetensors'))
        if set(incoming)!=keys:raise ValueError('Adapter tensor keys differ')
        for key,value in incoming.items():
            if value.shape!=weights[key].shape:raise ValueError('Adapter tensor shapes differ')
            weights[key]+=value.float()/len(sources)
    if not all(bool(value.isfinite().all()) for value in weights.values()):raise ValueError('Averaged weights are not finite')
    output.mkdir(parents=True)
    for path in root.iterdir():
        if path.is_file() and path.name not in {'adapter_model.safetensors','training_report.json'}:shutil.copyfile(path,output/path.name)
    save_file(weights,str(output/'adapter_model.safetensors'),metadata={'format':'pt'})
    report={'schema_version':1,'base_model':history['base_model'],'base_revision':history['base_revision'],
        'tokenizer_sha256':history['tokenizer_sha256'],'parent':str(root),'parent_files':snapshots[str(root)],
        'parent_training_report_sha256':digest(root/'training_report.json'),'train_examples':history['train_examples'],
        'training':{**history['training'],'metrics_scope':'Inherited historical parent training metrics; this averaging operation performed zero gradient updates.'},
        'inherited_training_history':history,'transformation':{'method':'equal_weight_same_lineage_adapter_parameter_mean',
            'sources':snapshots,'weight_per_source':1/len(sources),'tensor_count':len(weights),
            'seconds':time.perf_counter()-started,'optimizer_steps':0,'training_tokens':0},
        'objective':'weight-space-stability-export','weights_reinitialized':False,'original_checkpoints_modified':False,
        'promoted':False,'automatic_promotion':False,'evaluation_pending':True}
    for source in sources:
        if inventory(source)!=snapshots[str(source)]:raise ValueError('An original checkpoint changed during averaging')
    (output/'training_report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parent',type=Path,required=True)
    parser.add_argument('--reference',type=Path,action='append',required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(stabilize(args.parent,args.reference,args.output),indent=2))


if __name__=='__main__':main()
