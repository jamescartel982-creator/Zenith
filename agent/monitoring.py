"""Bounded local metadata, private aggregates, and workload-qualified drift signals."""
import argparse
from collections import defaultdict
import json
import platform
import time
from .quality import percentile,configuration_signature
from . import __version__


class Monitor:
    def __init__(self,store):
        self.store=store
        with store.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS generation_metrics (
                id INTEGER PRIMARY KEY, created REAL NOT NULL, user_id TEXT NOT NULL,
                session_id TEXT NOT NULL, status TEXT NOT NULL, configuration TEXT NOT NULL,
                provider TEXT NOT NULL, mode TEXT NOT NULL, style TEXT NOT NULL, method TEXT NOT NULL,
                elapsed_ms REAL NOT NULL, first_text_ms REAL, input_tokens INTEGER, output_tokens INTEGER,
                model_calls INTEGER, capped INTEGER NOT NULL)''')
            db.execute('CREATE INDEX IF NOT EXISTS metrics_user ON generation_metrics(user_id,id)')

    def record(self,settings,user_id,session_id,status,performance,method):
        usage=performance.get('usage') or {}
        with self.store.connect() as db:
            db.execute('''INSERT INTO generation_metrics
                (created,user_id,session_id,status,configuration,provider,mode,style,method,elapsed_ms,first_text_ms,input_tokens,output_tokens,model_calls,capped)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(
                time.time(),user_id or '',session_id,status,configuration_signature(settings,performance['response_mode'],performance['reply_style']),
                settings.provider,performance['response_mode'],performance['reply_style'],method,performance['elapsed_ms'],performance.get('first_text_ms'),
                usage.get('input_tokens'),usage.get('output_tokens'),usage.get('model_calls'),int(usage.get('finish_reason')=='length')))
            db.execute('DELETE FROM generation_metrics WHERE created<?',(time.time()-30*86400,))
            db.execute('DELETE FROM generation_metrics WHERE id NOT IN (SELECT id FROM generation_metrics ORDER BY id DESC LIMIT 1000)')

    def summary(self,user_id=None,all_users=False):
        with self.store.connect() as db:
            db.execute('DELETE FROM generation_metrics WHERE created<?',(time.time()-30*86400,))
            rows=db.execute('SELECT * FROM generation_metrics'+('' if all_users else ' WHERE user_id=?')+' ORDER BY id DESC LIMIT 1000',
                            () if all_users else (user_id or '__not_signed_in__',)).fetchall()
        rows=[dict(row) for row in rows];complete=[r for r in rows if r['status']=='completed'];model=[r for r in complete if r['method']=='model']
        known=[r for r in complete if r['output_tokens'] is not None]
        def times(group):
            return {'requests':len(group),'total_p50_ms':percentile([r['elapsed_ms'] for r in group],.5),
                    'total_p95_ms':percentile([r['elapsed_ms'] for r in group],.95),
                    'first_text_p50_ms':percentile([r['first_text_ms'] for r in group if r['first_text_ms'] is not None],.5)}
        groups=defaultdict(list)
        for row in model:groups[(row['configuration'],row['provider'],row['mode'],row['style'])].append(row)
        cohorts=[];signals=[]
        for (signature,provider,mode,style),group in groups.items():
            cohorts.append({'configuration':signature,'provider':provider,'mode':mode,'reply_style':style,**times(group)})
            # Only like-configured, model-generated requests are compared. Workload
            # and output lengths still differ; this is never an accuracy judgment.
            if len(group)>=40:
                recent=percentile([r['elapsed_ms'] for r in group[:20]],.5);previous=percentile([r['elapsed_ms'] for r in group[20:40]],.5)
                if previous and recent>previous*1.5:
                    signals.append({'kind':'latency-increase','provider':provider,'mode':mode,'reply_style':style,'ratio':round(recent/previous,2),
                                    'note':'Inspect workload, output lengths, cold loads and hardware; this is not proof of model quality drift.'})
        return {'scope':'server' if all_users else 'your-account','retention':'Latest 1000 started requests globally, up to 30 days; conversation deletion removes linked metrics.',
                'requests':len(rows),'completed':len(complete),'failed':sum(r['status']=='failed' for r in rows),
                'cancelled':sum(r['status']=='cancelled' for r in rows),'all_paths':times(complete),'model_generated':times(model),
                'reported_token_requests':len(known),'reported_input_tokens':sum(r['input_tokens'] for r in complete if r['input_tokens'] is not None),
                'reported_output_tokens':sum(r['output_tokens'] for r in known),'capped_replies':sum(r['capped'] for r in complete),
                'cohorts':cohorts,'signals':signals,'quality_drift':'Use the independent labeled benchmark workflow; production latency does not measure factual accuracy.',
                'privacy':'No prompt, response, memory text, secret code or tool input is stored in performance records.'}


def system_snapshot(agent,user_id=None):
    settings=agent.settings;team=agent.team_info();knowledge=agent.store.knowledge_stats()
    notes=len(agent.personal.memories(user_id)) if user_id else 0
    providers=list(agent.provider.providers.values()) if isinstance(getattr(agent.provider,'providers',None),dict) else [agent.provider]
    devices=[]
    for provider in providers:
        model=getattr(provider,'model',None);device=getattr(model,'device',None)
        if device is not None and str(device).split(':')[0] in {'cpu','cuda','mps'}:devices.append(str(device))
    components=[
        {'id':'model','name':'AI model','status':'Configured','summary':'The selected local neural model generates replies; only configured contributors run.',
         'details':[f"Provider: {settings.provider}",f"Configured models: {len(team['members'])}",f"Requested device: {settings.device}",
                    'Loaded device: '+(', '.join(sorted(set(devices))) if devices else 'Not loaded here or managed by the local endpoint')],
         'models':team['members']},
        {'id':'harness','name':'Harness','status':'Running','summary':'Responsive browser chat, streaming HTTP API, and installed terminal interface.',
         'details':['Fast routing or thorough team deliberation','Auto, Brief and Full reply budgets','Safe Markdown, explicit feedback and cancellation']},
        {'id':'context','name':'Context / memory','status':'Local','summary':'Recent conversation turns, your explicitly saved notes, and cited retrieved excerpts ground each request.',
         'details':[f'Your saved notes: {notes}',f"Shared indexed documents: {knowledge['documents']}",f'Brief history: last {settings.fast_history_turns} turns; full history: last 12',
                    'Earlier turns remain saved; only a bounded selection is sent to the model.']},
        {'id':'infrastructure','name':'Infrastructure & data pipeline','status':'Configured','summary':'Local inference, SQLite WAL/FTS5 retrieval, versioned imports, and isolated candidate training.',
         'details':[f'Python {platform.python_version()} · {platform.system()}',f'CPU thread limit: {settings.cpu_threads}',
                    'PyTorch selects CPU, CUDA or MPS when available; local endpoints manage their own hardware.',
                    'Retrieval is lexical FTS5, not a vector database. Corpus snapshots → cleaning/grouping → train/validation/test → reviewed candidate.']},
        {'id':'governance','name':'Governance & monitoring','status':'Active','summary':'Account isolation, owner elevation, explicit training approval, abstention, and local performance records.',
         'details':['No arbitrary model-triggered shell or tool execution','Bounded metadata retention; private account aggregates and owner-only server view',
                    'Versioned task/slice evaluation and scheduled regression checks; no automatic model promotion',
                    'Model confidence remains uncalibrated without a matching validated artifact.']},
    ]
    return {'version':__version__,'components':components,'limits':{'max_new_tokens':settings.max_new_tokens,'brief_max_new_tokens':min(settings.max_new_tokens,settings.fast_max_new_tokens),
            'context_tokens':settings.context_tokens,'default_reply_style':settings.reply_style,'default_response_mode':settings.response_mode},
            'metrics_available':bool(user_id),'monitoring_is_local':True}


def main():
    parser=argparse.ArgumentParser(description='Inspect local Zenith components and aggregate performance as the OS owner')
    parser.add_argument('--metrics',action='store_true');args=parser.parse_args()
    from .core import Agent
    agent=Agent()
    print(json.dumps(agent.monitor.summary(all_users=True) if args.metrics else system_snapshot(agent),indent=2))


if __name__=='__main__':main()
