"""Deterministic routing tests for SEP ticket status questions."""
import unittest
from unittest.mock import patch
from ai.agent.orchestrator import AgentOrchestrator


class TicketStatusPhrasingTests(unittest.TestCase):
    def test_my_ticket_status_without_number_lists_personal_tickets(self):
        samples = (
            'Check my ticket status',
            'Please check my ticket status',
            'Show my ticket status',
            'Give me my ticket status',
            'What is the status of my tickets?',
            'What are the statuses of my tickets?',
            'Show my tickets progress',
            'Can you check my ticket status?',
            'Give me an update on my tickets',
            'Track my ticket status',
        )
        agent = AgentOrchestrator()
        with patch.object(agent.llm, 'chat', side_effect=AssertionError('Should not call LLM')):
            for query in samples:
                with self.subTest(query=query):
                    result = agent.understand_request(query)
                    self.assertEqual(result['intent'], 'SEARCH_TICKETS')
                    self.assertEqual(result['search_scope'], 'MY_TICKETS')
                    self.assertIsNone(result['search_query'])
                    self.assertFalse(result['ticket_count_only'])
                    self.assertEqual(result['missing_fields'], [])

    def test_specific_ticket_number_uses_detail_lookup(self):
        agent = AgentOrchestrator()
        with patch.object(agent.llm, 'chat', side_effect=AssertionError('Should not call LLM')):
            result = agent.understand_request('Check my ticket INC-00029 status')
            self.assertEqual(result['intent'], 'CHECK_TICKET_STATUS')
            self.assertEqual(result['ticket_number'], 'INC-00029')
            self.assertEqual(result['ticket_query'], 'STATUS')

    def test_personal_ticket_status_with_keyword(self):
        agent = AgentOrchestrator()
        with patch.object(agent.llm, 'chat', side_effect=AssertionError('Should not call LLM')):
            result = agent.understand_request('Check my laptop ticket status')
            self.assertEqual(result['intent'], 'SEARCH_TICKETS')
            self.assertEqual(result['search_scope'], 'MY_TICKETS')
            self.assertEqual(result['search_query'], 'laptop')

if __name__ == '__main__':
    unittest.main()
