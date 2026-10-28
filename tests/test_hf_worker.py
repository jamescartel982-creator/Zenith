"""Streaming completion/cancellation ordering, without optional ML dependencies."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import queue
import sys
from threading import Event,Thread,get_ident
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agent.config import Settings
from agent.providers import HuggingFaceProvider


END=object()


class Streamer:
    def __init__(self,*args,**kwargs):self.queue=queue.Queue()
    def __iter__(self):return self
    def __next__(self):
        value=self.queue.get(timeout=.5)
        if value is END:raise StopIteration
        return value
    def put_text(self,text):self.queue.put(text)
    def end(self):self.queue.put(END)


class HFWorkerTests(unittest.TestCase):
    def setUp(self):
        self.patchers=[patch.dict(sys.modules,{'transformers':SimpleNamespace(TextIteratorStreamer=Streamer)}),
            patch('agent.providers._initialize_hf_worker',lambda *args:None)]
        for patcher in self.patchers:patcher.start();self.addCleanup(patcher.stop)
        self.provider=HuggingFaceProvider(replace(Settings(),provider='huggingface',kv_cache_mb=1))
        self.provider.model=SimpleNamespace(device=SimpleNamespace(type='cpu'))
        self.provider.tokenizer=object()
        self.provider.load=lambda:None
        self.provider._prepare=lambda messages,settings:(None,messages)
        self.addCleanup(self.provider.close)

    def test_reuses_a_single_owned_worker_across_streams(self):
        identifiers=[]
        def generate(ids,settings,cancel,streamer,scope):
            identifiers.append(get_ident());streamer.put_text('OK');streamer.end()
        self.provider._generate=generate
        for _ in range(3):self.assertEqual(list(self.provider.stream([],Event())),[('OK',[])])
        self.assertEqual(len(set(identifiers)),1)

    def test_http_stream_can_resume_and_finish_on_a_different_worker_thread(self):
        def generate(ids,settings,cancel,streamer,scope):
            streamer.put_text('first');streamer.put_text('second');streamer.end()
        self.provider._generate=generate
        stream=self.provider.stream([],Event())
        self.assertEqual(next(stream),('first',[]))
        with ThreadPoolExecutor(max_workers=1) as consumer:
            self.assertEqual(consumer.submit(lambda:list(stream)).result(timeout=5),[('second',[])])
        # The lock must be released for the next request, not stranded on the
        # thread that first advanced the previous stream.
        self.assertEqual(list(self.provider.stream([],Event())),[('first',[]),('second',[])])

    def test_http_disconnect_can_close_the_stream_on_a_different_worker_thread(self):
        cancel=Event()
        def generate(ids,settings,cancel,streamer,scope):
            streamer.put_text('partial')
            if not cancel.wait(5):raise RuntimeError('Missing disconnect cancellation')
            streamer.end()
        self.provider._generate=generate
        stream=self.provider.stream([],cancel)
        self.assertEqual(next(stream),('partial',[]))
        with ThreadPoolExecutor(max_workers=1) as consumer:
            consumer.submit(stream.close).result(timeout=5)
        self.assertTrue(cancel.is_set())
        self.assertTrue(self.provider._generation_lock.acquire(blocking=False))
        self.provider._generation_lock.release()

    def test_end_of_text_does_not_cancel_post_generation_cache_admission(self):
        release=Event();joining=Event();admitted=[];errors=[];cancel=Event()
        executor=ThreadPoolExecutor(max_workers=1)
        class TrackedFuture:
            def __init__(self,future):self.future=future
            def done(self):return self.future.done()
            def result(self):joining.set();return self.future.result()
        class TrackedWorker:
            def submit(self,*args):return TrackedFuture(executor.submit(*args))
        self.provider._worker=lambda:TrackedWorker()
        def generate(ids,settings,cancel,streamer,scope):
            streamer.put_text('OK');streamer.end()
            if not release.wait(5):raise RuntimeError('Fixture cleanup was not released')
            if not cancel.is_set():admitted.append(scope)
        self.provider._generate=generate
        def consume():
            try:list(self.provider.stream_scoped([],cancel,('alice','one')))
            except BaseException as error:errors.append(error)
        consumer=Thread(target=consume)
        consumer.start()
        try:
            self.assertTrue(joining.wait(5))
            self.assertFalse(cancel.is_set())
        finally:
            release.set();consumer.join(5);executor.shutdown(wait=True)
        self.assertFalse(consumer.is_alive());self.assertFalse(errors)
        self.assertEqual(admitted,[('alice','one')]);self.assertTrue(cancel.is_set())

    def test_cancellation_while_joining_late_work_discards_its_cache_entry(self):
        release=Event();joining=Event();cancel=Event();errors=[]
        executor=ThreadPoolExecutor(max_workers=1)
        class Future:
            def __init__(self,future):self.future=future
            def done(self):return self.future.done()
            def result(self):joining.set();return self.future.result()
        class Worker:
            def submit(self,*args):return Future(executor.submit(*args))
        self.provider._worker=lambda:Worker()
        def generate(ids,settings,cancel,streamer,scope):
            streamer.end();release.wait(5)
        self.provider._generate=generate
        def consume():
            try:list(self.provider.stream_scoped([],cancel,('alice','one')))
            except BaseException as error:errors.append(error)
        with patch.object(self.provider._prefix_cache,'discard') as discard:
            consumer=Thread(target=consume);consumer.start()
            try:
                self.assertTrue(joining.wait(5));cancel.set()
            finally:
                release.set();consumer.join(5);executor.shutdown(wait=True)
            self.assertFalse(errors);self.assertFalse(consumer.is_alive())
            discard.assert_called_once_with(('alice','one'))

    def test_early_close_cancels_before_join_and_discards_attention_state(self):
        cancel=Event();finished=Event();scope=('alice','one')
        def generate(ids,settings,cancel,streamer,scope):
            streamer.put_text('partial')
            if not cancel.wait(5):raise RuntimeError('Cancellation never arrived')
            finished.set();streamer.end()
        self.provider._generate=generate
        with patch.object(self.provider._prefix_cache,'discard') as discard:
            stream=self.provider.stream_scoped([],cancel,scope)
            self.assertEqual(next(stream),('partial',[]));stream.close()
            self.assertTrue(finished.is_set());discard.assert_called_once_with(scope)

    def test_errors_after_stream_end_are_not_silently_accepted(self):
        def generate(ids,settings,cancel,streamer,scope):
            streamer.end();raise RuntimeError('post-generation failure')
        self.provider._generate=generate
        with patch.object(self.provider._prefix_cache,'discard') as discard:
            with self.assertRaisesRegex(RuntimeError,'streaming generation failed'):
                list(self.provider.stream_scoped([],Event(),('alice','failed')))
            discard.assert_called_once_with(('alice','failed'))


if __name__=='__main__':unittest.main()
