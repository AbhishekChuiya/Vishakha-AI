import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
class Oct14Refinements(unittest.TestCase):
    def test_server_pins_are_scoped_per_application(self):
        text=(ROOT/'apps/assistant/views.py').read_text(encoding='utf-8')
        self.assertIn('user=request.user, application=application, pinned=True',text)
    def test_browser_pin_scope(self):
        text=(ROOT/'static/js/chat.js').read_text(encoding='utf-8')
        self.assertIn('Boolean(item.pinned) && applicationForChat(item) === selectedVishakhaApp',text)
    def test_short_ticket_request_fallback_is_existing_intent(self):
        text=(ROOT/'ai/agent/orchestrator.py').read_text(encoding='utf-8')
        self.assertIn('Short employee shorthand should be understood',text)
        self.assertNotIn("'intent':'CLARIFY_TICKET_ACTION'",text)
    def test_two_distinct_workspaces(self):
        text=(ROOT/'static/js/dashboard.js').read_text(encoding='utf-8')
        self.assertIn("set('darpan-sep-recent-count'",text)
        self.assertIn("if(id!=='total')set('darpan-sep-'",text)
    def test_dropdown_checkmarks_removed(self):
        text=(ROOT/'templates/assistant/index.html').read_text(encoding='utf-8')
        self.assertNotIn('class="application-active-mark"',text)
if __name__=='__main__':unittest.main()
