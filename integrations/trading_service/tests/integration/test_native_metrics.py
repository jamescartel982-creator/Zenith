"""Run in the independently installed native SDK environment."""
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from zenith_trading_service.metrics import NativeMetrics


class NativeMetricsTests(unittest.TestCase):
    def test_counters_deduplicate_and_never_persist_model_messages(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/'metrics.json';metrics=NativeMetrics(file)
            metrics.on_chat_model_start({'private':'fixture-secret'},['fixture-secret'],run_id='one')
            metrics.on_chat_model_start({},[],run_id='one')
            metrics.on_llm_end(SimpleNamespace(llm_output={'token_usage':{'prompt_tokens':37,'completion_tokens':2}}),run_id='one')
            metrics.on_llm_end(SimpleNamespace(llm_output={}),run_id='one')
            metrics.on_chat_model_start({},[],run_id='two')
            metrics.on_llm_error(ValueError('fixture-secret'),run_id='two')
            value=json.loads(file.read_text())
            self.assertEqual(value['llm_calls_started'],2);self.assertEqual(value['llm_calls_completed'],1)
            self.assertEqual(value['llm_calls_failed'],1);self.assertEqual(value['active_llm_calls'],0)
            self.assertEqual(value['input_tokens'],37);self.assertEqual(value['output_tokens'],2)
            self.assertNotIn('fixture-secret',file.read_text())
