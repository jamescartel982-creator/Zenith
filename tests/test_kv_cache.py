"""Attention state cannot cross owners, sessions, expiry or memory limits."""
from types import SimpleNamespace
import unittest

from agent.kv_cache import ScopedKVCache


class Storage:
    def __init__(self,size):self.size=size
    def data_ptr(self):return id(self)
    def nbytes(self):return self.size


class Tensor:
    device='cpu'
    def __init__(self,size=512):self.storage=Storage(size)
    def untyped_storage(self):return self.storage


class Past:
    def __init__(self,length=64,size=512,sliding=False):
        self.length=length
        self.layers=[SimpleNamespace(keys=Tensor(size),values=Tensor(size),is_sliding=sliding)]
    def get_seq_length(self):return self.length
    def crop(self,length):self.length=min(self.length,length)


class KVCacheTests(unittest.TestCase):
    def test_other_users_and_conversations_cannot_reuse_identical_private_tokens(self):
        cache=ScopedKVCache(10000);tokens=list(range(64));past=Past()
        self.assertTrue(cache.put(('alice','one'),tokens,past))
        self.assertEqual(cache.take(('bob','one'),tokens+[65]),(None,0))
        self.assertEqual(cache.take(('alice','other'),tokens+[65]),(None,0))
        self.assertEqual(cache.take(None,tokens+[65]),(None,0))
        self.assertEqual(cache.take(('alice','one'),tokens+[65]),(past,64))
        self.assertEqual(cache.bytes,0)
        self.assertEqual(cache.take(('alice','one'),tokens+[65]),(None,0))

    def test_exact_prefix_crop_never_uses_changed_text_or_an_empty_decoder_input(self):
        cache=ScopedKVCache(20000);scope=('alice','one');tokens=list(range(100))
        past=Past(100);cache.put(scope,tokens,past)
        self.assertEqual(cache.take(scope,tokens[:50]+[999]+tokens[51:]),(past,50))
        self.assertEqual(past.length,50)
        past=Past(100);cache.put(scope,tokens,past)
        self.assertEqual(cache.take(scope,tokens),(past,99))
        cache.put(scope,tokens,Past(100))
        self.assertEqual(cache.take(scope,[999]+tokens),(None,0))

    def test_expiry_entry_limit_and_discard_release_account_state(self):
        now=[0];cache=ScopedKVCache(50000,ttl=10,maximum_entries=2,clock=lambda:now[0])
        tokens=list(range(64))
        for session in ('one','two','three'):cache.put(('alice',session),tokens,Past())
        self.assertNotIn(('alice','one'),cache.entries)
        cache.discard(('alice','two'));self.assertNotIn(('alice','two'),cache.entries)
        self.assertGreater(cache.bytes,0)
        now[0]=11
        self.assertEqual(cache.take(('alice','three'),tokens+[65]),(None,0))
        self.assertEqual(cache.bytes,0)
        cache.put(('alice','four'),tokens,Past());cache.clear()
        self.assertEqual(cache.bytes,0);self.assertFalse(cache.entries)

    def test_physical_storage_budget_and_unsupported_caches_are_enforced(self):
        cache=ScopedKVCache(10000);scope=('alice','one');tokens=list(range(64))
        self.assertFalse(cache.put(scope,tokens,Past(size=10000)))
        self.assertFalse(cache.put(scope,tokens,Past(sliding=True)))
        self.assertFalse(cache.put(scope,tokens,Past(63)))
        self.assertFalse(cache.put(scope,tokens,object()))
        self.assertFalse(ScopedKVCache(0).put(scope,tokens,Past()))
        for session in range(10):cache.put(('alice',str(session)),tokens,Past())
        self.assertLessEqual(cache.bytes,10000)
        self.assertLess(len(cache.entries),10)

    def test_invalid_scope_and_configuration_never_create_entries(self):
        cache=ScopedKVCache(10000)
        for scope in [None,('alice',),('alice',''),('alice',3),['alice','one'],('alice','x'*257)]:
            self.assertFalse(cache.put(scope,list(range(64)),Past()))
        for kwargs in [dict(maximum_bytes=-1),dict(maximum_bytes=True),dict(maximum_bytes=1,ttl=0),
                dict(maximum_bytes=1,maximum_entries=0),dict(maximum_bytes=1,minimum_prefix=0)]:
            with self.assertRaises(ValueError):ScopedKVCache(**kwargs)


if __name__=='__main__':unittest.main()
