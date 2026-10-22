"""Focused language preference tests without needing live SEP or a running LLM."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace

BASE = Path(__file__).resolve().parents[1]
source = (BASE / 'apps' / 'assistant' / 'views.py').read_text(encoding='utf8')
module = ast.parse(source)
namespace = {'re': __import__('re')}
for node in module.body:
    if isinstance(node, ast.FunctionDef) and node.name in ('_general_language_instruction', '_rewrite_general_followup_prompt'):
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(BASE / 'apps' / 'assistant' / 'views.py'), 'exec'), namespace)

class FakeMessages:
    def __init__(self, messages): self.items = messages
    def order_by(self, *_): return self.items

class LanguageTests(unittest.TestCase):
    def test_unknown_preference_falls_back(self):
        self.assertEqual(namespace['_general_language_instruction']('nonsense'), '')

    def test_hinglish_preference(self):
        self.assertIn('Hinglish', namespace['_general_language_instruction']('hinglish'))

    def test_hindi_preference(self):
        self.assertIn('Devanagari', namespace['_general_language_instruction']('hindi'))

    def test_translation_followup(self):
        conversation = SimpleNamespace(messages=FakeMessages([
            SimpleNamespace(role='assistant', content='Please paste the message you want to translate into Hindi.'),
            SimpleNamespace(role='user', content='Translate a message into Hindi'),
        ]))
        rewritten = namespace['_rewrite_general_followup_prompt']('you dont know anything about me, just give me one chance', conversation)
        self.assertIn('Translate the following message into Hindi', rewritten)
        self.assertIn('just give me one chance', rewritten)

    def test_normal_followup_not_rewritten(self):
        conversation = SimpleNamespace(messages=FakeMessages([
            SimpleNamespace(role='assistant', content='What would you like to know?'),
            SimpleNamespace(role='user', content='Hello'),
        ]))
        self.assertEqual(namespace['_rewrite_general_followup_prompt']('Tell me about the company', conversation), 'Tell me about the company')

if __name__ == '__main__': unittest.main()
