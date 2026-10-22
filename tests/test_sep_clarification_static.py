import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class ClarificationContractTests(unittest.TestCase):
    def test_backend_clarification_has_safe_prompts(self):
        code = (ROOT/'ai/agent/workflow.py').read_text()
        self.assertIn('"type": "clarification"', code)
        self.assertIn('"prompt": "Create a ticket"', code)
        self.assertIn('"prompt": "Show my tickets"', code)
        self.assertNotIn("I couldn't understand that request reliably", code)

    def test_frontend_recognizes_clarification_and_sends_text(self):
        code = (ROOT/'static/js/chat.js').read_text()
        self.assertIn('result.type === "clarification"', code)
        self.assertIn("sendToBackend(prompt, 'text')", code)
        self.assertIn("event.target.closest('.darpan-clarification-choice')", code)

    def test_mobile_styles_present(self):
        code = (ROOT/'static/css/main.css').read_text()
        self.assertIn('.darpan-clarification-card', code)
        self.assertIn('.darpan-clarification-actions', code)

if __name__ == '__main__': unittest.main()
