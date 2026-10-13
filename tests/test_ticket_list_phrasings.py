"""Regression tests for semantically equivalent SEP listing requests."""
import unittest
from unittest.mock import patch
from ai.agent.orchestrator import AgentOrchestrator

class TicketListPhrasingTests(unittest.TestCase):
    def test_personal_ticket_phrasings_do_not_call_llm(self):
        samples = (
            'show my tickets', 'give me my tickets', 'get my tickets',
            'display my tickets', 'list my tickets', 'provide my tickets',
            'fetch my tickets', 'what tickets have I raised?',
            'I want to see my tickets', 'can you show my tickets?',
            'could you give me my tickets?',
        )
        agent = AgentOrchestrator()
        with patch.object(agent.llm, 'chat', side_effect=AssertionError('Should not call LLM')):
            for query in samples:
                with self.subTest(query=query):
                    out = agent.understand_request(query)
                    self.assertEqual(out['intent'], 'SEARCH_TICKETS')
                    self.assertEqual(out['search_scope'], 'MY_TICKETS')
                    self.assertIsNone(out['search_query'])
                    self.assertFalse(out['ticket_count_only'])

    def test_filters_and_meaningful_keywords(self):
        agent = AgentOrchestrator()
        with patch.object(agent.llm, 'chat', side_effect=AssertionError('Should not call LLM')):
            open_result = agent.understand_request('give me my open tickets')
            self.assertEqual(open_result['ticket_status_filter'], 'OPEN')
            self.assertIsNone(open_result['search_query'])
            result = agent.understand_request('find my laptop tickets')
            self.assertEqual(result['search_query'], 'laptop')
            self.assertEqual(result['search_scope'], 'MY_TICKETS')

if __name__ == '__main__':
    unittest.main()
