"""The separate provider is explicit; native source, execution grants and tools stay intact."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

from zenith_integrations.openclaw.adapter import message_text, quality_flags


class ProfileTests(unittest.TestCase):
    def test_each_frozen_case_requires_its_own_successful_projection(self):
        script=Path(__file__).parent/'integration/native_openclaw.py'
        spec=importlib.util.spec_from_file_location('native_measurement',script)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        metrics=[]
        for case,question in [('addition','What is 2 plus 2?'),('multiplication','What is 7 multiplied by 8?'),('instruction','Reply with exactly ZENITH')]:
            messages=[SimpleNamespace(role='user',content=question)]
            metrics.append(module.projection_metrics(messages,case,question))
            self.assertTrue(module.case_projection_verified(metrics,case))
        self.assertFalse(module.case_projection_verified(metrics,'missing'))
        metrics.append(module.projection_metrics([SimpleNamespace(role='user',content='Other request')],'instruction','Reply with exactly ZENITH'))
        self.assertFalse(module.case_projection_verified(metrics,'instruction'))
        self.assertTrue(module.case_projection_verified(metrics,'multiplication'))

    def test_provider_is_explicitly_allowlisted_and_tools_stay_disabled(self):
        script=Path(__file__).parent/'integration/native_openclaw.py'
        spec=importlib.util.spec_from_file_location('native_profile',script)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        config=module.profile(Path('/private/state'),18789,'http://127.0.0.1:8781')
        self.assertEqual(config['plugins']['allow'],['zenith-local-context'])
        self.assertTrue(Path(config['plugins']['load']['paths'][0],'openclaw.plugin.json').is_file())
        self.assertEqual(config['tools'],{'deny':['*']})
        self.assertEqual(config['agents']['defaults']['model']['fallbacks'],[])
        legacy=module.profile(Path('/private/state'),18789,'http://127.0.0.1:8781',False)
        self.assertEqual(legacy['plugins'],{'enabled':False})
        self.assertEqual(config | {'plugins':None},legacy | {'plugins':None})

    def test_text_extraction_never_marks_arbitrary_answers_verified(self):
        self.assertEqual(message_text({'content':[{'type':'text','text':'4'}]}),'4')
        self.assertEqual(quality_flags({'content':'none in the latest retained-input page'}),['native_context_echo'])
        self.assertEqual(quality_flags({'content':'## Temporal Context\nCurrent date: 2026-10-28\nTime zone: UTC'}),['native_context_echo'])
        self.assertEqual(quality_flags({'content':[{'type':'text','text':42}]}),['native_answer_not_verified'])


if __name__=='__main__':unittest.main()
