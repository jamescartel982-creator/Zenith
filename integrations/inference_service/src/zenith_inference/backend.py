"""Actual inference over the preserved checkpoint; no tool execution or training."""
from dataclasses import dataclass
import queue
import threading

from . import identity
from .limits import ContextExceeded, InferenceCancelled


@dataclass
class Completion:
    text: str
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str


class BoundedQueue(queue.Queue):
    def __init__(self, cancellation):
        super().__init__(maxsize=32)
        self.cancellation = cancellation

    def put(self, value, block=True, timeout=None):
        while not self.cancellation.cancelled():
            try:
                return super().put(value, timeout=0.05)
            except queue.Full:
                continue


class NativeBackend:
    def __init__(self, manifest, limits):
        self.manifest, self.limits = manifest, limits
        self.model = self.tokenizer = None
        self.identity_hash = None
        self.load_lock = threading.Lock()
        self.generation_lock = threading.Lock()

    def load(self):
        with self.load_lock:
            if self.model is not None:
                return
            record, signature = identity.verify(self.manifest)
            import torch
            from agent.checkpoints import load_existing, tokenizer_signature
            from agent.providers import select_device
            from agent.tokenization import load_preserved_tokenizer
            from transformers import AutoModelForCausalLM
            threads = record['cpu_threads']
            torch.set_num_threads(threads)
            if record['adapter']:
                model, tokenizer, details = load_existing(record['adapter'], trainable=False, cpu_threads=threads)
                if details['base_model'] != record['model'] or details['base_revision'] != record['revision']:
                    raise ValueError('The verified adapter lineage changed')
            else:
                tokenizer = load_preserved_tokenizer(record['base_directory'], local_files_only=True)
                model, info = AutoModelForCausalLM.from_pretrained(record['base_directory'], local_files_only=True,
                    trust_remote_code=False, use_safetensors=True, dtype=torch.float32, output_loading_info=True)
                if any(info.get(k) for k in ['missing_keys', 'unexpected_keys', 'mismatched_keys', 'error_msgs']):
                    raise ValueError('Exact trained weights did not load; initialization is forbidden')
            if tokenizer_signature(tokenizer) != record['tokenizer_sha256']:
                raise ValueError('The saved tokenizer identity changed')
            if len(tokenizer) > model.get_input_embeddings().weight.shape[0]:
                raise ValueError('Tokenizer is incompatible with existing embeddings')
            if identity.verify(self.manifest)[1] != signature:
                raise ValueError('Artifacts changed while loading')
            device = select_device(torch, record['device'])
            model.to(device)
            if device != 'cpu':
                model.half()
            model.requires_grad_(False)
            model.eval()
            self.record, self.model, self.tokenizer, self.identity_hash = record, model, tokenizer, signature

    def complete(self, request, cancellation, emit=None):
        cancellation.check()
        self.load()
        import torch
        from transformers import StoppingCriteria, StoppingCriteriaList, TextIteratorStreamer
        with self.generation_lock:
            cancellation.check()
            maximum = request.maximum or self.limits.max_output_tokens
            if maximum > self.limits.max_output_tokens:
                raise ContextExceeded('Requested output exceeds the configured service budget')
            if request.tools and '<tool_call>' not in self.tokenizer.chat_template:
                raise ContextExceeded('This saved template does not support the implemented tool protocol')
            messages = request.native_messages()
            tools = [tool.model_dump(exclude_none=True) for tool in request.tools or []] if request.tool_choice != 'none' else None
            # Use the actual saved template, including its native tool history.
            encoded = self.tokenizer.apply_chat_template(messages, tools=tools, tokenize=True,
                        add_generation_prompt=True, return_dict=False)
            architectural = self.model.config.max_position_embeddings
            if len(encoded) > self.limits.context_tokens or len(encoded) + maximum > architectural:
                raise ContextExceeded('Complete message/tool history exceeds the context budget; no history was silently removed')
            ids = torch.tensor([encoded], device=self.model.device)
            class Stop(StoppingCriteria):
                def __call__(self, *args, **kwargs):
                    return cancellation.cancelled()
            options = {'do_sample': request.temperature > 0}
            if request.temperature > 0:
                options.update(temperature=request.temperature, top_p=request.top_p or 0.9)
            else:
                options.update(temperature=None, top_p=None, top_k=None)
            streamer = None
            if emit:
                streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True, timeout=0.1)
                streamer.text_queue = BoundedQueue(cancellation)
            outputs, errors = [], []
            def generate():
                try:
                    if self.model.device.type == 'cpu':
                        torch.set_num_threads(self.record['cpu_threads'])
                    with torch.inference_mode():
                        outputs.append(self.model.generate(input_ids=ids, attention_mask=torch.ones_like(ids),
                            max_new_tokens=maximum, use_cache=True, pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
                            stopping_criteria=StoppingCriteriaList([Stop()]), streamer=streamer, **options))
                except Exception as exc:
                    errors.append(exc)
                    if streamer:
                        streamer.end()
            if streamer:
                worker = threading.Thread(target=generate, name='zenith-inference-generation', daemon=False)
                worker.start()
                completed = False
                try:
                    while worker.is_alive() or not streamer.text_queue.empty():
                        cancellation.check()
                        try:
                            chunk = next(streamer)
                        except queue.Empty:
                            continue
                        except StopIteration:
                            break
                        if chunk:
                            emit(chunk)
                    completed = True
                finally:
                    if not completed:
                        cancellation.event.set()
                    worker.join()
            else:
                generate()
            cancellation.check()
            if errors:
                raise RuntimeError('Verified model inference failed') from errors[0]
            output = outputs[0][0, len(encoded):]
            count = len(output)
            eos = self.model.generation_config.eos_token_id
            eos = eos if isinstance(eos, list) else [eos]
            finish = 'stop' if count and int(output[-1]) in eos else 'length'
            text = self.tokenizer.decode(output, skip_special_tokens=True).strip()
            return Completion(text, len(encoded), count, finish)
