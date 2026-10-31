"""Open-model inference without paid API keys or arbitrary remote Python code."""
from contextlib import closing

import requests
from .policy import AUTHORITY_POLICY

from .transport import (
    ProviderProtocolError, delta_text, final_text, json_object,
    ndjson_objects, sse_payloads,
)

SYSTEM_PROMPT = (
    "You are Zenith, an independent AI assistant. Be thoughtful, warm, and precise. " + AUTHORITY_POLICY +
    "Answer the user's actual question directly, then explain when useful. "
    "Use readable paragraphs and Markdown when appropriate. Follow explicit output-format requests; "
    "return raw JSON or code without wrappers when requested. "
    "Ask focused questions when essential information is missing. Distinguish facts "
    "from assumptions; never invent citations, tool results, or remembered facts. "
    "Be honest about uncertainty. You can discuss and write code, but cannot "
    "execute tools, change your own weights, or deploy applications from chat."
)


def token_usage(input_tokens,output_tokens,source='provider-reported',finish_reason=None):
    values=[v if type(v) is int and 0<=v<=10**9 else None for v in (input_tokens,output_tokens)]
    return {'input_tokens':values[0],'output_tokens':values[1],
            'total_tokens':sum(values) if all(v is not None for v in values) else None,
            'source':source,'model_calls':1,'finish_reason':finish_reason if finish_reason in {'stop','length'} else None}


def hf_usage(model,output,input_length,maximum):
    count=output.shape[1]-input_length
    eos=model.generation_config.eos_token_id
    eos=eos if isinstance(eos,list) else [eos]
    ended=count>0 and int(output[0,-1]) in eos
    return token_usage(input_length,count,'model-tokenizer','stop' if ended or count<maximum else 'length')


def select_device(torch, requested):
    if requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def trim_messages(messages, fits):
    """Drop complete oldest turns, preserving system and current user message."""
    result = [dict(m) for m in messages]
    while not fits(result):
        if len(result) <= 2:
            raise ValueError("Message exceeds the model context budget. Shorten it or increase CONTEXT_TOKENS.")
        del result[1:3]
    return result


def _initialize_hf_worker(cpu_threads, device_type):
    if device_type == 'cpu':
        import torch
        torch.set_num_threads(cpu_threads)


class HuggingFaceProvider:
    def __init__(self, settings):
        from threading import Lock, RLock
        from .kv_cache import ScopedKVCache
        self.settings = settings
        self.model = None
        self.tokenizer = None
        self._load_lock = RLock()
        # HTTP streaming may advance/close the generator on different worker
        # threads. Unlike RLock, Lock permits its owner to transfer on a yield.
        self._generation_lock = Lock()
        self._generation_worker = None
        self._prefix_cache = ScopedKVCache(getattr(settings,'kv_cache_mb',0) * 1024 * 1024)

    def load(self):
        with self._load_lock:
            self._load()

    def _load(self):
        if self.model is not None:
            return
        if self.settings.checkpoint_receipt:
            from .deployment import validate_activation
            validate_activation(self.settings)
        try:
            import torch
            from transformers import AutoModelForCausalLM
        except ImportError as exc:
            raise RuntimeError('Install local inference: pip install -e ".[local]"') from exc
        settings = self.settings
        device = select_device(torch, settings.device)
        if device == "cpu":
            torch.set_num_threads(settings.cpu_threads)
        dtype = torch.float32 if device == "cpu" else torch.float16
        from .tokenization import load_preserved_tokenizer
        tokenizer = load_preserved_tokenizer(settings.model, revision=settings.revision, local_files_only=settings.offline)
        if not tokenizer.chat_template:
            raise ValueError("Choose an instruction/chat model with a chat template")
        model = AutoModelForCausalLM.from_pretrained(
            settings.model, revision=settings.revision, dtype=dtype,
            trust_remote_code=False, use_safetensors=True, local_files_only=settings.offline).to(device)
        if settings.adapter:
            from peft import PeftModel, PeftConfig
            adapter_config = PeftConfig.from_pretrained(settings.adapter, local_files_only=settings.offline)
            if adapter_config.base_model_name_or_path != settings.model:
                raise ValueError("ZENITH_ADAPTER was trained on a different HF_MODEL")
            model = PeftModel.from_pretrained(model, settings.adapter, local_files_only=settings.offline)
        model.eval()
        self._prefix_cache.clear()
        self.tokenizer, self.model = tokenizer, model

    def _worker(self):
        # The initializer holds no reference to this provider. Dropping an idle
        # provider can therefore release its executor and loaded model normally.
        if self._generation_worker is None:
            from concurrent.futures import ThreadPoolExecutor
            self._generation_worker = ThreadPoolExecutor(max_workers=1,
                thread_name_prefix='zenith-generation', initializer=_initialize_hf_worker,
                initargs=(self.settings.cpu_threads, self.model.device.type))
        return self._generation_worker

    def close(self):
        with self._generation_lock:
            worker,self._generation_worker = self._generation_worker,None
            if worker is not None:
                worker.shutdown(wait=True,cancel_futures=True)
            self._prefix_cache.clear()

    def _prepare(self, messages, settings):
        import torch
        encoded = None
        budget = min(settings.context_tokens,
            getattr(self.model.config,'max_position_embeddings',32768)-settings.max_new_tokens)
        def fits(items):
            nonlocal encoded
            encoded=self.tokenizer.apply_chat_template(items,tokenize=True,return_dict=False,add_generation_prompt=True)
            return len(encoded)<=budget
        used=trim_messages(messages,fits)
        # fits() already encoded the final retained history; do not repeat it.
        return torch.tensor([encoded],device=self.model.device),used

    def _generate(self, ids, settings, cancel=None, streamer=None, scope=None):
        import torch
        from transformers import StoppingCriteria,StoppingCriteriaList,DynamicCache
        class CancelGeneration(StoppingCriteria):
            def __call__(self,*args,**kwargs):return cancel is not None and cancel.is_set()
        options={'do_sample':settings.temperature>0}
        if settings.temperature>0:options.update(temperature=settings.temperature,top_p=0.9)
        else:options.update(temperature=None,top_p=None,top_k=None)
        # Explicitly scoped full-attention Qwen2 only. Other models, shared
        # native services and anonymous requests retain uncached generation.
        supported=(self._prefix_cache.maximum_bytes>0 and self._prefix_cache.valid_scope(scope)
            and getattr(self.model.config,'model_type',None)=='qwen2'
            and not getattr(self.model.config,'use_sliding_window',False))
        reused=0
        with torch.inference_mode():
            if cancel is not None and cancel.is_set():return None
            extra={}
            if supported:
                past,reused=self._prefix_cache.take(scope,ids[0].tolist())
                if past is not None:extra['past_key_values']=past
                extra['return_dict_in_generate']=True
            result=self.model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),
                max_new_tokens=settings.max_new_tokens,use_cache=True,
                pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
                streamer=streamer,stopping_criteria=StoppingCriteriaList([CancelGeneration()]),**extra,**options)
            output=result.sequences if supported else result
            # Removed cache entries are never reinserted after cancellation or
            # failure. The final generated token is not yet in the attention cache.
            if supported and (cancel is None or not cancel.is_set()):
                past=result.past_key_values
                if isinstance(past,DynamicCache):
                    length=past.get_seq_length()
                    if type(length) is int and 0<length<=output.shape[1]:
                        self._prefix_cache.put(scope,output[0,:length].tolist(),past)
            self.last_usage=hf_usage(self.model,output,ids.shape[1],settings.max_new_tokens)
            self.last_usage.update(reused_input_tokens=reused,computed_input_tokens=ids.shape[1]-reused)
            return output

    def generate(self, messages):
        with self._generation_lock:
            self.last_usage=None
            self.load()
            settings=self.settings
            ids,used=self._prepare(messages,settings)
            output=self._worker().submit(self._generate,ids,settings).result()
            return self.tokenizer.decode(output[0,ids.shape[1]:],skip_special_tokens=True).strip(),used

    def stream(self, messages, cancel):
        return self._stream(messages,cancel,None)

    def stream_scoped(self, messages, cancel, scope):
        """Internal caller supplies the authenticated user and owned conversation."""
        return self._stream(messages,cancel,scope)

    def _stream(self, messages, cancel, scope):
        import queue
        from transformers import TextIteratorStreamer
        with self._generation_lock:
            self.last_usage=None
            self.load()
            settings=self.settings
            ids,used=self._prepare(messages,settings)
            streamer=TextIteratorStreamer(self.tokenizer,skip_prompt=True,skip_special_tokens=True,timeout=0.5)
            errors=[]
            def work():
                try:self._generate(ids,settings,cancel,streamer,scope)
                except Exception as exc:
                    errors.append(exc);streamer.end()
            worker=self._worker().submit(work)
            finished=False
            try:
                while not cancel.is_set():
                    try:chunk=next(streamer)
                    except queue.Empty:
                        if worker.done():break
                        continue
                    except StopIteration:
                        finished=True;break
                    if chunk and not cancel.is_set():yield chunk,used
            finally:
                aborted=not finished or cancel.is_set()
                if aborted:cancel.set()
                try:worker.result()
                finally:
                    if aborted or cancel.is_set() or errors:self._prefix_cache.discard(scope)
                    cancel.set()
            if errors:raise RuntimeError('Model streaming generation failed') from errors[0]


class OllamaProvider:
    def __init__(self, settings):
        self.settings = settings

    def generate(self, messages):
        self.last_usage = None
        s = self.settings
        # Conservative byte budget: Ollama tokenizes the final request itself.
        used = trim_messages(messages, lambda items: sum(len(m["content"].encode("utf-8")) + 32 for m in items) <= s.context_tokens)
        try:
            response = requests.post(f"{s.ollama_url}/api/chat", json={
                "model": s.ollama_model, "stream": False, "messages": used,
                "options": {"temperature": s.temperature, "num_predict": s.max_new_tokens,
                            "num_ctx": s.context_tokens + s.max_new_tokens},
            }, timeout=(10, 300), allow_redirects=False)
            with closing(response):
                if response.is_redirect is True:
                    raise ProviderProtocolError('Ollama endpoint redirected; check its configured URL')
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict) or data.get('error') or data.get('done') is False:
                    raise ProviderProtocolError('Ollama returned an invalid or incomplete chat response')
                content = final_text(data['message']['content'])
                self.last_usage = token_usage(data.get('prompt_eval_count'), data.get('eval_count'),
                                              finish_reason=data.get('done_reason'))
        except requests.RequestException as exc:
            raise RuntimeError(f"Cannot reach Ollama or its model. Run: ollama pull {s.ollama_model}") from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("Ollama returned an invalid chat response") from exc
        return content, used

    def stream(self, messages, cancel):
        self.last_usage = None
        if cancel.is_set():
            return
        s = self.settings
        used = trim_messages(messages, lambda items: sum(len(m['content'].encode('utf-8')) + 32 for m in items) <= s.context_tokens)
        response = requests.post(s.ollama_url + '/api/chat', json={
            'model': s.ollama_model, 'messages': used, 'stream': True,
            'options': {'temperature': s.temperature, 'num_predict': s.max_new_tokens,
                        'num_ctx': s.context_tokens + s.max_new_tokens},
        }, stream=True, timeout=(10, 300), allow_redirects=False)
        with closing(response):
            if response.is_redirect:
                raise ProviderProtocolError('Ollama streaming endpoint redirected')
            response.raise_for_status()
            for row in ndjson_objects(response, cancel):
                if cancel.is_set():
                    return
                message = row.get('message', {})
                if not isinstance(message, dict) or type(row.get('done', False)) is not bool:
                    raise ProviderProtocolError('Ollama returned an invalid stream event')
                chunk = delta_text(message.get('content'))
                if chunk:
                    yield chunk, used
                if cancel.is_set():
                    return
                if row.get('done') is True:
                    self.last_usage = token_usage(row.get('prompt_eval_count'), row.get('eval_count'),
                                                  finish_reason=row.get('done_reason'))
                    return
            if not cancel.is_set():
                raise ProviderProtocolError('Ollama stream ended before its completion event; retry the answer')


class TinyProvider:
    def __init__(self, settings):
        self.settings = settings
        self.model = None

    def generate(self, messages):
        self.last_usage=None
        import torch
        from .tiny import load_checkpoint, encode, decode
        if self.model is None:
            self.model = load_checkpoint(self.settings.tiny_checkpoint, select_device(torch, self.settings.device))
        def prompt(items):
            return "".join(f'{m["role"].capitalize()}: {m["content"]}\n' for m in items) + "Assistant:"
        used = trim_messages(messages, lambda items: len(encode(prompt(items))) <= self.model.config.context_length)
        ids = torch.tensor([encode(prompt(used))], device=next(self.model.parameters()).device)
        output = self.model.generate(ids, self.settings.max_new_tokens, self.settings.temperature)
        self.last_usage=token_usage(ids.shape[1],output.shape[1]-ids.shape[1],'utf8-byte-tokenizer','length')
        return decode(output[0, ids.shape[1]:].tolist()), used


class LocalServerProvider:
    """llama.cpp/vLLM-compatible local chat endpoint. Never sends an API key."""
    def __init__(self, settings):
        self.settings = settings

    def generate(self, messages):
        self.last_usage=None
        s = self.settings
        used = trim_messages(messages, lambda items: sum(len(m['content'].encode('utf-8')) + 32 for m in items) <= s.context_tokens)
        try:
            response = requests.post(s.local_server_url + '/chat/completions', json={
                'model': s.local_server_model, 'messages': used, 'stream': False,
                'max_tokens': s.max_new_tokens, 'temperature': s.temperature,
            }, timeout=(10, 300), allow_redirects=False)
            with closing(response):
                if response.is_redirect is True:
                    raise ProviderProtocolError('Local model endpoint redirected')
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict) or data.get('error'):
                    raise ProviderProtocolError('Local model server reported an invalid response')
                choice = data['choices'][0]
                if choice.get('finish_reason') not in {None, 'stop', 'length'}:
                    raise ProviderProtocolError('Local model did not complete a text answer')
                content = final_text(choice['message']['content'])
                counts = data.get('usage') or {}
                self.last_usage = token_usage(counts.get('prompt_tokens'), counts.get('completion_tokens'),
                                              finish_reason=choice.get('finish_reason'))
        except requests.RequestException as exc:
            raise RuntimeError('Start your local model server and verify its model alias and /v1 endpoint') from exc
        except (AttributeError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError('Local server returned no valid final chat response') from exc
        return content, used

    def stream(self, messages, cancel):
        self.last_usage = None
        if cancel.is_set():
            return
        s = self.settings
        used = trim_messages(messages, lambda items: sum(len(m['content'].encode('utf-8')) + 32 for m in items) <= s.context_tokens)
        response = requests.post(s.local_server_url + '/chat/completions', json={
            'model': s.local_server_model, 'messages': used, 'stream': True,
            'stream_options': {'include_usage': True}, 'max_tokens': s.max_new_tokens,
            'temperature': s.temperature,
        }, stream=True, timeout=(10, 300), allow_redirects=False)
        usage = None
        finish_reason = None
        completed = False
        with closing(response):
            if response.is_redirect:
                raise ProviderProtocolError('Local model streaming endpoint redirected')
            response.raise_for_status()
            for payload in sse_payloads(response, cancel):
                if cancel.is_set():
                    return
                if payload.strip() == '[DONE]':
                    completed = True
                    break
                row = json_object(payload)
                counts = row.get('usage')
                if counts is not None:
                    if not isinstance(counts, dict):
                        raise ProviderProtocolError('Local model returned invalid usage metadata')
                    usage = counts
                choices = row.get('choices', [])
                if not isinstance(choices, list) or len(choices) > 1:
                    raise ProviderProtocolError('Local model returned an unexpected choice list')
                if choices:
                    choice = choices[0]
                    if not isinstance(choice, dict) or not isinstance(choice.get('delta', {}), dict):
                        raise ProviderProtocolError('Local model returned an invalid choice')
                    chunk = delta_text(choice.get('delta', {}).get('content'))
                    if finish_reason is not None and chunk:
                        raise ProviderProtocolError('Local model sent text after completion')
                    reason = choice.get('finish_reason')
                    if reason is not None:
                        if reason not in ('stop', 'length'):
                            raise ProviderProtocolError('Local model did not complete a text answer')
                        finish_reason = reason
                    if chunk:
                        yield chunk, used
            if cancel.is_set():
                return
            if not completed and finish_reason is None:
                raise ProviderProtocolError('Local model stream ended before completion; retry the answer')
            counts = usage or {}
            self.last_usage = token_usage(counts.get('prompt_tokens'), counts.get('completion_tokens'),
                                          finish_reason=finish_reason)


def make_provider(settings):
    if settings.provider == 'reasoning':
        from .reasoning import ReasoningProvider
        return ReasoningProvider(settings)
    if settings.provider == 'orchestrated':
        from .orchestration import OrchestratedProvider
        return OrchestratedProvider(settings)
    if settings.provider == "ensemble":
        from .ensemble import EnsembleProvider
        return EnsembleProvider(settings)
    return {"huggingface": HuggingFaceProvider, "ollama": OllamaProvider, "tiny": TinyProvider, 'localserver': LocalServerProvider}[settings.provider](settings)
