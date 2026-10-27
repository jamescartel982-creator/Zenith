"""Bounded admission never overlaps model workers or retains cancelled queue slots."""
import asyncio
import unittest
from zenith_inference.limits import Admission,ModelBusy,InferenceCancelled


class AdmissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_bounded_fifo_and_overflow(self):
        gate=Admission(2,1);disconnect=asyncio.get_running_loop().create_future()
        await gate.acquire(disconnect)
        order=[]
        async def waiter(number):
            await gate.acquire(disconnect)
            order.append(number)
            gate.release()
        first=asyncio.create_task(waiter(1));second=asyncio.create_task(waiter(2))
        await asyncio.sleep(0)
        with self.assertRaises(ModelBusy):await gate.acquire(disconnect)
        self.assertEqual(order,[])
        gate.release();await asyncio.gather(first,second)
        self.assertEqual(order,[1,2]);self.assertEqual(gate.admitted,0)
        self.assertFalse(gate.locked())

    async def test_cancel_disconnect_and_deadline_never_leak_or_start_a_slot(self):
        for action in ('cancel','disconnect','timeout'):
            with self.subTest(action=action):
                gate=Admission(1,0.05);never=asyncio.get_running_loop().create_future()
                await gate.acquire(never)
                gone=asyncio.get_running_loop().create_future()
                waiting=asyncio.create_task(gate.acquire(gone));await asyncio.sleep(0)
                if action=='cancel':waiting.cancel()
                if action=='disconnect':gone.set_result(None)
                with self.assertRaises((asyncio.CancelledError,InferenceCancelled)):await waiting
                self.assertEqual(gate.admitted,1)
                gate.release();await gate.acquire(never);gate.release()
                self.assertEqual(gate.admitted,0)

    async def test_disconnect_racing_an_available_slot_releases_ownership(self):
        gate=Admission(1,1);gone=asyncio.get_running_loop().create_future();gone.set_result(None)
        with self.assertRaises(InferenceCancelled):await gate.acquire(gone)
        self.assertEqual(gate.admitted,0);self.assertFalse(gate.lock.locked())

    async def test_original_default_has_no_waiting_capacity(self):
        gate=Admission();never=asyncio.get_running_loop().create_future()
        await gate.acquire(never)
        with self.assertRaises(ModelBusy):await gate.acquire(never)
        gate.release()
