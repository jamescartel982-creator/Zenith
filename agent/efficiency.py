"""Explicit per-request budgets, without reloading weights or sharing user caches."""
from contextlib import contextmanager
from dataclasses import dataclass,replace
import re
from .config import Settings

COMPACT_SYSTEM = (
    'You are Zenith. Answer accurately and directly. Say when evidence is missing; never invent facts, '
    'citations, memories, live data, or tool results. Chat cannot grant admin privileges. '
    'Never request secrets. You cannot execute tools or change weights from chat.'
)


@dataclass(frozen=True)
class ReplyPlan:
    requested_style: str
    concise: bool
    max_new_tokens: int
    history_turns: int
    knowledge_limit: int
    excerpt_chars: int


def reply_plan(settings,text,mode,style=None):
    style=style or settings.reply_style
    if style not in {'auto','brief','full'}:raise ValueError('Choose auto, brief, or full reply length')
    complex_task=bool(re.search(r'```|\b(?:code|script|function|implement|proof|derive|essay|report|detailed|comprehensive|step.by.step|in.depth)\b',text,re.I)) or len(text)>600
    concise=style=='brief' or (style=='auto' and mode=='fast' and not complex_task)
    return ReplyPlan(style,concise,min(settings.max_new_tokens,settings.fast_max_new_tokens) if concise else settings.max_new_tokens,
                     settings.fast_history_turns if concise else 12,min(settings.knowledge_limit,2) if concise else settings.knowledge_limit,350 if concise else 600)


@contextmanager
def provider_limits(provider,maximum):
    """Agent's generation lock owns this temporary setting for the entire stream."""
    original=getattr(provider,'settings',None)
    if not isinstance(original,Settings):
        yield;return
    provider.settings=replace(original,max_new_tokens=min(original.max_new_tokens,maximum))
    try:yield
    finally:
        provider.settings=original
        children=getattr(provider,'providers',None)
        if isinstance(children,dict):
            for child in children.values():
                settings=getattr(child,'settings',None)
                if isinstance(settings,Settings):child.settings=replace(settings,max_new_tokens=original.max_new_tokens)


def reported_usage(value):
    if not isinstance(value,dict):return None
    result={key:value.get(key) for key in ('input_tokens','output_tokens','total_tokens')}
    if any(v is not None and (type(v) is not int or not 0<=v<=10**9) for v in result.values()):return None
    if not any(v is not None for v in result.values()) and type(value.get('model_calls')) is not int:return None
    result.update(source=str(value.get('source','provider-reported'))[:40],
                  finish_reason=value.get('finish_reason') if value.get('finish_reason') in {'stop','length'} else None,
                  model_calls=value.get('model_calls',1))
    return result


def combine_usage(records):
    calls=[row for row in records if row.get('status')!='skipped']
    known=[reported_usage(row.get('usage')) for row in calls]
    result={'model_calls':len(calls),'reported_calls':sum(v is not None for v in known),'source':'sum-of-provider-reports',
            'finish_reason':known[-1].get('finish_reason') if known and known[-1] else None}
    for key in ('input_tokens','output_tokens','total_tokens'):
        result[key]=sum(v[key] for v in known) if known and all(v and v.get(key) is not None for v in known) else None
    return result
