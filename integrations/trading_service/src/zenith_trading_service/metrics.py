"""Native LLM callback counters only. No prompts, results, credentials or hidden traces."""
import json
import os
from pathlib import Path
import threading
import time
import uuid
from langchain_core.callbacks import BaseCallbackHandler
from zenith_integrations.shared.secrets import write_private_new


class NativeMetrics(BaseCallbackHandler):
    def __init__(self,path):
        self.path=Path(path);self.lock=threading.RLock();self.active={};self.finished=set()
        self.counts={'llm_calls_started':0,'llm_calls_completed':0,'llm_calls_failed':0,
                     'input_tokens':0,'output_tokens':0,'responses_with_usage':0}
        self.started=time.monotonic()

    def snapshot(self):
        with self.lock:
            return {**self.counts,'active_llm_calls':len(self.active),'elapsed_seconds':round(time.monotonic()-self.started,3),
                    'tool_network_time_measured':False,'callbacks_scope':'native model clients, not all graph/tool events'}

    def persist(self):
        with self.lock:
            value=self.snapshot()
            temporary=self.path.with_name('.metrics-'+uuid.uuid4().hex)
            write_private_new(temporary,json.dumps(value)+'\n');os.replace(temporary,self.path)

    def on_chat_model_start(self,serialized,messages,*,run_id,**kwargs):
        with self.lock:
            if run_id not in self.active and run_id not in self.finished:
                self.active[run_id]=time.monotonic();self.counts['llm_calls_started']+=1
        self.persist()

    def on_llm_end(self,response,*,run_id,**kwargs):
        with self.lock:
            if run_id in self.finished:return
            self.active.pop(run_id,None);self.finished.add(run_id);self.counts['llm_calls_completed']+=1
            usage=(response.llm_output or {}).get('token_usage',{})
            incoming,outgoing=usage.get('prompt_tokens'),usage.get('completion_tokens')
            if type(incoming) is int and type(outgoing) is int and 0<=incoming<=10**9 and 0<=outgoing<=10**9:
                self.counts['input_tokens']+=incoming;self.counts['output_tokens']+=outgoing;self.counts['responses_with_usage']+=1
        self.persist()

    def on_llm_error(self,error,*,run_id,**kwargs):
        with self.lock:
            if run_id in self.finished:return
            self.active.pop(run_id,None);self.finished.add(run_id);self.counts['llm_calls_failed']+=1
        self.persist()
