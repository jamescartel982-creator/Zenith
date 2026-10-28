"""Reports must describe the exact selected preserved model, not just an adapter."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from agent.config import Settings
from scripts.inference_speed_benchmark import validate_selection


class BenchmarkIdentityTests(unittest.TestCase):
    def test_changed_revision_model_or_adapter_is_rejected_before_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            settings=replace(Settings(),provider='huggingface',adapter=directory)
            record={'model':settings.model,'revision':settings.revision,'adapter':str(Path(directory).resolve())}
            validate_selection(settings,record)
            for changed in (replace(settings,revision='0'*40),replace(settings,model='different/model'),
                            replace(settings,adapter=''),replace(settings,adapter=directory+'/other')):
                with self.assertRaises(ValueError):validate_selection(changed,record)


if __name__=='__main__':unittest.main()
