"""The separate provider is explicit; native source, execution grants and tools stay intact."""
import importlib.util
from pathlib import Path
import unittest

from zenith_integrations.openclaw.adapter import message_text, quality_flags


class ProfileTests(unittest.TestCase):
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
        self.assertEqual(quality_flags({'content':[{'type':'text','text':42}]}),['native_answer_not_verified'])


if __name__=='__main__':unittest.main()
