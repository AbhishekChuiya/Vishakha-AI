"""Regression tests for interruptions in an unfinished SEP ticket workflow.

Uses the actual process_message method isolated from API dependencies.
"""
import ast
import re
import unittest
from pathlib import Path
from unittest.mock import Mock

PATH = Path(__file__).resolve().parents[1] / 'ai' / 'agent' / 'workflow.py'
source = ast.parse(PATH.read_text(encoding='utf-8'))
workflow_class = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == 'AgentWorkflow')
process = next(node for node in workflow_class.body if isinstance(node, ast.FunctionDef) and node.name == 'process_message')
slim_class = ast.ClassDef(name='WorkflowHarness', bases=[], keywords=[], body=[process], decorator_list=[])
code = compile(ast.fix_missing_locations(ast.Module(body=[slim_class], type_ignores=[])), str(PATH), 'exec')
namespace = {'re': re}
exec(code, namespace)

class DraftState:
    def __init__(self):
        self.current_question = 'priority'
        self.department = 'IT Department'
        self.description = 'Laptop display flickering'
        self.intent = 'CREATE_TICKET'
        self.ticket_number = None
        self.saved = None
    def to_dict(self):
        return {'current_question': self.current_question, 'department': self.department,
                'description': self.description, 'intent': self.intent}
    def from_dict(self, data):
        self.__dict__.update(data)
    def reset(self):
        self.current_question = None
        self.description = None
        self.department = None
        self.intent = None
    def update_from_agent(self, data):
        self.intent = data.get('intent')
        self.ticket_number = data.get('ticket_number')

class PendingDraftTests(unittest.TestCase):
    def setUp(self):
        self.w = namespace['WorkflowHarness']()
        self.w.state = DraftState()
        self.w.orchestrator = Mock()
        self.w.handle_search_tickets = Mock(return_value={'type':'ticket_search', 'tickets':[]})
        self.w.handle_ticket_analytics = Mock(return_value={'type':'message', 'message':'Report'})
        self.w.handle_create_ticket = Mock(return_value={'type':'question','field':'department'})
        self.w.handle_ticket_status = Mock(return_value={'type':'message','message':'Open'})
        self.w.handle_option = Mock(return_value={'type':'question','field':'priority'})
        self.w.cancel = Mock(return_value={'type':'message','message':'Cancelled'})

    def test_read_only_search_preserves_pending_draft(self):
        self.w.orchestrator.understand_request.return_value = {'intent':'SEARCH_TICKETS'}
        result = self.w.process_message('Show my tickets')
        self.assertTrue(result['draft_preserved'])
        self.assertEqual(self.w.state.current_question,'priority')
        self.assertEqual(self.w.state.description,'Laptop display flickering')
        self.w.handle_search_tickets.assert_called_once()

    def test_read_only_analytics_preserves_pending_draft(self):
        self.w.orchestrator.understand_request.return_value = {'intent':'ANALYZE_TICKETS'}
        result = self.w.process_message('Give me summary of IT Department tickets')
        self.assertTrue(result['draft_preserved'])
        self.assertEqual(self.w.state.current_question,'priority')

    def test_unrelated_question_does_not_discard_draft(self):
        self.w.orchestrator.understand_request.return_value = {'intent':'GENERAL_CHAT'}
        result = self.w.process_message('Explain artificial intelligence')
        self.assertTrue(result['draft_preserved'])
        self.assertEqual(self.w.state.current_question,'priority')

    def test_explicit_new_ticket_starts_new_workflow(self):
        self.w.orchestrator.understand_request.return_value = {'intent':'CREATE_TICKET'}
        result = self.w.process_message('Create a new ticket')
        self.assertTrue(result['workflow_interrupted'])
        self.assertIsNone(self.w.state.description)
        self.w.handle_create_ticket.assert_called_once()

    def test_field_answer_remains_field_answer(self):
        result = self.w.process_message('High')
        self.assertEqual(result['field'],'priority')
        self.w.handle_option.assert_called_once_with('High')

if __name__ == '__main__': unittest.main()
