"""Open-model inference without paid API keys or arbitrary remote Python code."""
import requests

SYSTEM_PROMPT = (
    "You are Zenith, an independent AI assistant. Be thoughtful, warm, and precise. "
    "Answer the user's actual question directly, then explain when useful. "
    "Use readable paragraphs, Markdown, and fenced code for runnable examples. "
    "Ask focused questions when essential information is missing. Distinguish facts "
    "from assumptions; never invent citations, tool results, or remembered facts. "
    "Be honest about uncertainty. You can discuss and write code, but cannot "
    "execute tools, change your own weights, or deploy applications from chat."
)


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


class HuggingFaceProvider:
    def __init__(self, settings):
        self.settings = settings
        self.model = None
        self.tokenizer = None

    def load(self):
        if self.model is not None:
            return
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError('Install local inference: pip install -e ".[local]"') from exc
        settings = self.settings
        device = select_device(torch, settings.device)
        if device == "cpu":
            torch.set_num_threads(settings.cpu_threads)
        dtype = torch.float32 if device == "cpu" else torch.float16
        tokenizer = AutoTokenizer.from_pretrained(settings.model, revision=settings.revision, trust_remote_code=False, local_files_only=settings.offline)
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
        self.tokenizer, self.model = tokenizer, model

    def generate(self, messages):
        self.load()
        import torch
        tokenizer, model, settings = self.tokenizer, self.model, self.settings
        def encode(items):
            return tokenizer.apply_chat_template(items, tokenize=True, add_generation_prompt=True)
        max_position = getattr(model.config, "max_position_embeddings", 32768)
        budget = min(settings.context_tokens, max_position - settings.max_new_tokens)
        used = trim_messages(messages, lambda items: len(encode(items)) <= budget)
        ids = torch.tensor([encode(used)], device=model.device)
        options = {"do_sample": settings.temperature > 0}
        if settings.temperature == 0:
            options.update(temperature=None, top_p=None, top_k=None)
        if settings.temperature > 0:
            options.update(temperature=settings.temperature, top_p=0.9)
        with torch.inference_mode():
            output = model.generate(
                input_ids=ids, attention_mask=torch.ones_like(ids),
                max_new_tokens=settings.max_new_tokens,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id, **options)
        return tokenizer.decode(output[0, ids.shape[1]:], skip_special_tokens=True).strip(), used

    def stream(self, messages, cancel):
        """Yield text while generation runs; cancellation joins the worker before reuse."""
        self.load()
        import queue
        from threading import Thread
        import torch
        from transformers import TextIteratorStreamer, StoppingCriteria, StoppingCriteriaList
        tokenizer,model,settings=self.tokenizer,self.model,self.settings
        def encode(items):return tokenizer.apply_chat_template(items,tokenize=True,add_generation_prompt=True)
        maximum=getattr(model.config,'max_position_embeddings',32768)
        used=trim_messages(messages,lambda items:len(encode(items))<=min(settings.context_tokens,maximum-settings.max_new_tokens))
        ids=torch.tensor([encode(used)],device=model.device)
        streamer=TextIteratorStreamer(tokenizer,skip_prompt=True,skip_special_tokens=True,timeout=0.5)
        class CancelGeneration(StoppingCriteria):
            def __call__(self,*args,**kwargs):return cancel.is_set()
        options={'do_sample':settings.temperature>0}
        if settings.temperature>0:options.update(temperature=settings.temperature,top_p=0.9)
        else:options.update(temperature=None,top_p=None,top_k=None)
        errors=[]
        def work():
            try:
                if model.device.type=='cpu':torch.set_num_threads(settings.cpu_threads)
                with torch.inference_mode():
                    model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),max_new_tokens=settings.max_new_tokens,
                        pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,streamer=streamer,
                        stopping_criteria=StoppingCriteriaList([CancelGeneration()]),**options)
            except Exception as exc:
                errors.append(exc);streamer.end()
        worker=Thread(target=work,name='zenith-generation',daemon=False);worker.start()
        try:
            while not cancel.is_set():
                try:chunk=next(streamer)
                except queue.Empty:
                    if not worker.is_alive():break
                    continue
                except StopIteration:break
                if chunk:yield chunk,used
            if errors:raise RuntimeError('Model streaming generation failed') from errors[0]
        finally:
            cancel.set();worker.join()


class OllamaProvider:
    def __init__(self, settings):
        self.settings = settings

    def generate(self, messages):
        s = self.settings
        # Conservative byte budget: Ollama tokenizes the final request itself.
        used = trim_messages(messages, lambda items: sum(len(m["content"].encode("utf-8")) + 32 for m in items) <= s.context_tokens)
        try:
            response = requests.post(f"{s.ollama_url}/api/chat", json={
                "model": s.ollama_model, "stream": False, "messages": used,
                "options": {"temperature": s.temperature, "num_predict": s.max_new_tokens,
                            "num_ctx": s.context_tokens + s.max_new_tokens},
            }, timeout=(10, 300))
            response.raise_for_status()
            content = response.json()["message"]["content"]
        except requests.RequestException as exc:
            raise RuntimeError(f"Cannot reach Ollama or its model. Run: ollama pull {s.ollama_model}") from exc
        except (KeyError, ValueError) as exc:
            raise RuntimeError("Ollama returned an invalid chat response") from exc
        return content, used

    def stream(self,messages,cancel):
        import json
        s=self.settings
        used=trim_messages(messages,lambda items:sum(len(m['content'].encode('utf-8'))+32 for m in items)<=s.context_tokens)
        with requests.post(s.ollama_url+'/api/chat',json={'model':s.ollama_model,'messages':used,'stream':True,
            'options':{'temperature':s.temperature,'num_predict':s.max_new_tokens,'num_ctx':s.context_tokens+s.max_new_tokens}},stream=True,timeout=(10,300)) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if cancel.is_set():break
                if not line:continue
                row=json.loads(line)
                if row.get('error'):raise RuntimeError('Ollama streaming failed')
                chunk=row.get('message',{}).get('content','')
                if chunk:yield chunk,used


class TinyProvider:
    def __init__(self, settings):
        self.settings = settings
        self.model = None

    def generate(self, messages):
        import torch
        from .tiny import load_checkpoint, encode, decode
        if self.model is None:
            self.model = load_checkpoint(self.settings.tiny_checkpoint, select_device(torch, self.settings.device))
        def prompt(items):
            return "".join(f'{m["role"].capitalize()}: {m["content"]}\n' for m in items) + "Assistant:"
        used = trim_messages(messages, lambda items: len(encode(prompt(items))) <= self.model.config.context_length)
        ids = torch.tensor([encode(prompt(used))], device=next(self.model.parameters()).device)
        output = self.model.generate(ids, self.settings.max_new_tokens, self.settings.temperature)
        return decode(output[0, ids.shape[1]:].tolist()), used


class LocalServerProvider:
    """llama.cpp/vLLM-compatible local chat endpoint. Never sends an API key."""
    def __init__(self, settings):
        self.settings = settings

    def generate(self, messages):
        s = self.settings
        used = trim_messages(messages, lambda items: sum(len(m['content'].encode('utf-8')) + 32 for m in items) <= s.context_tokens)
        try:
            response = requests.post(s.local_server_url + '/chat/completions', json={
                'model': s.local_server_model, 'messages': used, 'stream': False,
                'max_tokens': s.max_new_tokens, 'temperature': s.temperature,
            }, timeout=(10, 300), allow_redirects=False)
            if response.is_redirect is True:
                raise requests.RequestException('Local model endpoint redirected')
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content']
            if not isinstance(content, str) or not content.strip():
                raise ValueError('No final text returned; increase the output budget for a reasoning model')
        except requests.RequestException as exc:
            raise RuntimeError('Start your local model server and verify its model alias and /v1 endpoint') from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError('Local server returned no valid final chat response') from exc
        return content, used

    def stream(self,messages,cancel):
        import json
        s=self.settings
        used=trim_messages(messages,lambda items:sum(len(m['content'].encode('utf-8'))+32 for m in items)<=s.context_tokens)
        with requests.post(s.local_server_url+'/chat/completions',json={'model':s.local_server_model,'messages':used,
            'stream':True,'max_tokens':s.max_new_tokens,'temperature':s.temperature},stream=True,
            timeout=(10,300),allow_redirects=False) as response:
            if response.is_redirect:raise RuntimeError('Local model streaming endpoint redirected')
            response.raise_for_status()
            for line in response.iter_lines():
                if cancel.is_set():break
                if not line or not line.startswith(b'data:'):continue
                payload=line[5:].strip()
                if payload==b'[DONE]':break
                row=json.loads(payload)
                if row.get('error'):raise RuntimeError('Local model streaming failed')
                choices=row.get('choices',[])
                if choices:
                    chunk=choices[0].get('delta',{}).get('content','')
                    if chunk:yield chunk,used


def make_provider(settings):
    if settings.provider == "ensemble":
        from .ensemble import EnsembleProvider
        return EnsembleProvider(settings)
    return {"huggingface": HuggingFaceProvider, "ollama": OllamaProvider, "tiny": TinyProvider, 'localserver': LocalServerProvider}[settings.provider](settings)
