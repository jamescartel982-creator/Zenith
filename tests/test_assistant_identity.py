"""Application identity must not be sampled from conflicting neural self-descriptions."""
from dataclasses import replace
import json
import secrets
import tempfile
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from agent.assurance import direct_answer, normalize_input
from agent.config import Settings
from agent.core import Agent
from agent.identity import identity_answer, model_provenance
from agent.server import create_app


class AssistantIdentityTests(unittest.TestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.settings=replace(Settings(), provider='huggingface', data_dir=directory.name,
                              model='Qwen/Qwen2.5-0.5B-Instruct', adapter='fixture-adapter-selection',
                              api_token=secrets.token_urlsafe(32), public_chat=True)
        self.provider=Mock()
        self.provider.generate.side_effect=lambda messages: ('I am Zeno, developed by Alibaba Cloud.', messages)
        self.agent=Agent(self.settings,self.provider)

    def test_common_identity_questions_are_application_facts_in_both_modes(self):
        questions=['Who created you','Who made you?', 'Who developed Zenith?', 'Who is your creator?',
                   'What is your name?', 'What’s your name?', 'Who are you?', 'Introduce yourself.',
                   'What model are you using?', 'Are you Zeno?', 'Can you tell me who built you?',
                   'What is your name and who created you?']
        for mode in ('fast','thorough'):
            for question in questions:
                with self.subTest(mode=mode,question=question):
                    result=self.agent.answer(question,str(uuid4()),response_mode=mode)
                    self.assertIn("I'm Zenith",result['response']); self.assertIn('n8storm',result['response'])
                    self.assertIn('Qwen/Qwen2.5-0.5B-Instruct',result['response'])
                    self.assertIn("Alibaba Cloud's Qwen team",result['response'])
                    self.assertNotIn('I am Zeno',result['response'])
                    self.assertEqual(result['quality']['verification'],'application-metadata')
                    self.assertIsNone(result['quality']['confidence'])
                    self.assertEqual(result['performance']['usage']['model_calls'],0)
                    self.assertEqual(result['sources'],[])
        self.provider.generate.assert_not_called()

    def test_other_people_code_quoted_text_and_formatting_requests_are_not_hijacked(self):
        for question in ['Who created Python?', 'Who created ChatGPT?', 'Who created the universe?',
                         'Translate "Who created you" into Spanish.', 'Explain the function created_by_you().',
                         'Who created you? Return JSON only.', 'Who created you in my novel?',
                         'What is your name in this Python class?', '```\nWho created you\n```']:
            with self.subTest(question=question):self.assertIsNone(identity_answer(question,self.settings))
        fullwidth=normalize_input('Ｗｈｏ ｃｒｅａｔｅｄ ｙｏｕ？')
        self.assertEqual(direct_answer(fullwidth,settings=self.settings)['method'],'application-identity')

    def test_unknown_or_switched_backends_do_not_inherit_alibaba_attribution_or_paths(self):
        for settings in [replace(self.settings,model='Example/OtherModel'),
                         replace(self.settings,model='/private/secret-checkpoint'),
                         replace(self.settings,provider='localserver'),
                         replace(self.settings,provider='tiny'),
                         replace(self.settings,provider='ollama')]:
            answer=identity_answer('Who created you?',settings)['text']
            self.assertIn('Zenith',answer);self.assertIn('n8storm',answer)
            self.assertNotIn('Alibaba',answer);self.assertNotIn('/private/',answer)
        self.assertNotIn('adapter',model_provenance(replace(self.settings,adapter='')))

    def test_actual_public_http_stream_ignores_old_wrong_identity_without_rewriting_it(self):
        client=TestClient(create_app(self.settings,self.agent),base_url='https://127.0.0.1')
        self.assertEqual(client.get('/api/account').status_code,200)
        session=str(uuid4())
        # Store the intentionally wrong provider output as earlier conversation history.
        old=client.post('/api/chat',json={'session_id':session,'message':'Say hello.'})
        self.assertEqual(old.status_code,200);self.assertIn('Zeno',old.json()['response'])
        stream=client.post('/api/chat/stream',json={'session_id':session,'message':'Who created you'})
        self.assertEqual(stream.status_code,200)
        events=[json.loads(line[6:]) for line in stream.text.splitlines() if line.startswith('data: ')]
        result=next(event['result'] for event in events if event['type']=='result')
        self.assertIn("I'm Zenith",result['response']);self.assertIn('n8storm',result['response'])
        self.assertEqual(''.join(e['text'] for e in events if e['type']=='delta'),result['response'])
        self.assertEqual(result['performance']['usage']['model_calls'],0)
        turns=client.get('/api/history/'+session).json()['turns']
        self.assertIn('Zeno',turns[0]['response']);self.assertIn("I'm Zenith",turns[1]['response'])
        self.assertEqual(self.provider.generate.call_count,1)
        self.assertEqual(client.get('/api/admin/help').status_code,401)

    def test_both_prompt_styles_have_the_same_identity_and_configured_provenance(self):
        for style in ('brief','full'):
            self.agent.answer('Explain who created you; answer in JSON.',str(uuid4()),reply_style=style)
            system=self.provider.generate.call_args.args[0][0]['content']
            self.assertIn('maintained by n8storm',system)
            self.assertIn('configured foundation model',system)
            self.assertIn("Alibaba Cloud's Qwen team",system)

    def test_unrelated_questions_do_not_receive_identity_prompt_expansion(self):
        for style in ('brief','full'):
            for question in ['Give a greeting in French.', 'Translate "Who created you" into Spanish.']:
                self.agent.answer(question,str(uuid4()),reply_style=style)
                system=self.provider.generate.call_args.args[0][0]['content']
                self.assertNotIn('maintained by n8storm',system)
                self.assertNotIn('Configured model provenance:',system)

    def test_calibration_fingerprint_changes_with_identity_policy(self):
        from agent.quality import configuration_signature
        baseline=configuration_signature(self.settings)
        with patch('agent.providers.SYSTEM_PROMPT','A different application identity policy'):
            self.assertNotEqual(baseline,configuration_signature(self.settings))


if __name__=='__main__':unittest.main()
