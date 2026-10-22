"""Focused tests that don't require a live Llama or SEP connection."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

class AutoLanguageRegressions(unittest.TestCase):
    def test_language_selector_removed(self):
        html = (ROOT/'templates/assistant/index.html').read_text(encoding='utf-8')
        js = (ROOT/'static/js/chat.js').read_text(encoding='utf-8')
        self.assertNotIn('id="darpan-language-preference"', html)
        self.assertNotIn('darpanResponseLanguage', js)
        self.assertIn('activeChatId !== requestChatId', js)

    def test_laptop_ticket_routes_to_it(self):
        # Stub model-only dependencies. This is a routing unit test, not API integration.
        llm_pkg = types.ModuleType('ai.llm.client')
        llm_pkg.LocalLLM = type('LocalLLM', (), {'__init__': lambda self: None})
        statuses = types.ModuleType('ai.agent.ticket_statuses')
        statuses.TICKET_STATUS_IDS = {}
        safety = types.ModuleType('ai.agent.input_safety')
        safety.meaningful_description = lambda s: bool(s)
        with patch.dict(sys.modules, {'ai.llm.client': llm_pkg, 'ai.agent.ticket_statuses': statuses, 'ai.agent.input_safety': safety}):
            import importlib.util
            spec = importlib.util.spec_from_file_location('darpan_orchestrator_test', ROOT/'ai/agent/orchestrator.py')
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            intent = mod.AgentOrchestrator().understand_request('Create a laptop repair ticket')
        self.assertEqual(intent['intent'], 'CREATE_TICKET')
        self.assertEqual(intent['department'], 'IT Department')

if __name__ == '__main__': unittest.main()
