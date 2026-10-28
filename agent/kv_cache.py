"""Bounded, transient attention state for one authenticated user/conversation.

This is not an answer cache. Every reply still runs model generation. Entries
are removed before mutation and are admitted again only after successful work.
"""
from collections import OrderedDict
from dataclasses import dataclass
import sys
from threading import RLock
import time


@dataclass
class Entry:
    tokens: tuple
    past: object
    bytes: int
    expires: float


class ScopedKVCache:
    def __init__(self, maximum_bytes, ttl=90, maximum_entries=8, minimum_prefix=32, clock=time.monotonic):
        if type(maximum_bytes) is not int or maximum_bytes<0 or not 0<ttl<=3600 or type(maximum_entries) is not int or not 1<=maximum_entries<=64 or type(minimum_prefix) is not int or minimum_prefix<1:
            raise ValueError('Use bounded KV cache size, expiry, entries and prefix length')
        self.maximum_bytes=maximum_bytes
        self.ttl,self.maximum_entries,self.minimum_prefix=ttl,maximum_entries,minimum_prefix
        self.clock=clock;self.entries=OrderedDict();self.bytes=0;self.lock=RLock()

    @staticmethod
    def valid_scope(scope):
        return isinstance(scope,tuple) and len(scope)==2 and all(isinstance(part,str) and 0<len(part)<=256 for part in scope)

    def _expire(self):
        now=self.clock()
        for scope in list(self.entries):
            if self.entries[scope].expires<=now:
                self.bytes-=self.entries.pop(scope).bytes

    def clear(self):
        with self.lock:
            self.entries.clear();self.bytes=0

    def discard(self, scope):
        if not self.valid_scope(scope):return
        with self.lock:
            entry=self.entries.pop(scope,None)
            if entry:self.bytes-=entry.bytes

    def take(self, scope, tokens):
        with self.lock:
            self._expire()
            if not self.maximum_bytes or not self.valid_scope(scope):return None,0
            entry=self.entries.pop(scope,None)
            if entry is None:return None,0
            self.bytes-=entry.bytes
            # Always leave an uncached final input token for generation. Compare
            # exact IDs, including roles and the saved tokenizer's delimiters.
            matched=0
            for old,new in zip(entry.tokens,tokens[:-1]):
                if old!=new:break
                matched+=1
            if matched<self.minimum_prefix:return None,0
            try:
                if entry.past.get_seq_length()!=len(entry.tokens):return None,0
                entry.past.crop(matched)
                if entry.past.get_seq_length()!=matched:return None,0
            except (AttributeError,TypeError,ValueError,NotImplementedError,RuntimeError):
                return None,0
            return entry.past,matched

    def put(self, scope, tokens, past):
        if not self.maximum_bytes or not self.valid_scope(scope):return False
        try:
            layers=past.layers
            if not layers or any(getattr(layer,'is_sliding',True) for layer in layers):return False
            if not callable(past.crop) or past.get_seq_length()!=len(tokens):return False
            storages=set();size=0
            for layer in layers:
                for tensor in (layer.keys,layer.values):
                    storage=tensor.untyped_storage()
                    key=(str(tensor.device),storage.data_ptr())
                    if key not in storages:
                        storages.add(key);size+=storage.nbytes()
            owned=tuple(tokens)
            size+=sys.getsizeof(owned)+sum(sys.getsizeof(token) for token in owned)
        except (AttributeError,TypeError,ValueError,NotImplementedError,RuntimeError):
            return False
        if not size or size>self.maximum_bytes:return False
        with self.lock:
            self._expire()
            previous=self.entries.pop(scope,None)
            if previous:self.bytes-=previous.bytes
            while self.entries and (self.bytes+size>self.maximum_bytes or len(self.entries)>=self.maximum_entries):
                _,old=self.entries.popitem(last=False);self.bytes-=old.bytes
            self.entries[scope]=Entry(owned,past,size,self.clock()+self.ttl);self.bytes+=size
        return True
