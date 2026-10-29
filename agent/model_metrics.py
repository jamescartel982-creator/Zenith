"""Report actual resident tensor counts; remote/configured-only models are unknown."""


def parameter_inventory(provider):
    model=getattr(provider,'model',None)
    if getattr(model,'is_quantized',False) is True or getattr(model,'is_loaded_in_4bit',False) is True:
        return {'status':'not-measured','total':None,'base':None,'lora':None,
                'note':'Packed/quantized tensor storage is not an architectural parameter count.'}
    names=getattr(model,'named_parameters',None)
    if not callable(names):
        return {'status':'not-measured','total':None,'base':None,'lora':None}
    total=lora=0
    try:
        for name,value in names():
            count=value.numel()
            if type(count) is not int or count<0:raise ValueError('Unknown parameter count')
            total+=count
            if 'lora_' in name:lora+=count
    except (AttributeError,TypeError,ValueError):
        return {'status':'not-measured','total':None,'base':None,'lora':None}
    if not total:
        return {'status':'not-measured','total':None,'base':None,'lora':None}
    configs=getattr(model,'peft_config',{})
    known_base=not configs or (isinstance(configs,dict) and all(getattr(item,'peft_type',None)=='LORA' for item in configs.values()))
    return {'status':'resident-tensors-counted','total':total,'base':total-lora if known_base else None,'lora':lora,
            'note':'Counts resident model tensors once, including LoRA. No weights were added, trained or loaded to obtain this count.'}
