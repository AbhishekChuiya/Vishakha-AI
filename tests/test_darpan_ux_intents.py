"""Run python -m unittest discover -s tests -p test_darpan_ux_intents.py"""
import unittest
from ai.agent.orchestrator import AgentOrchestrator

class UXIntentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = AgentOrchestrator()
        class NoLLM:
            def chat(self, *a, **k):
                raise AssertionError('These unambiguous commands must not invoke the LLM')
        cls.agent.llm = NoLLM()

    def test_top_it_application(self):
        v=self.agent.understand_request('Show top 10 IT Application')
        self.assertEqual(v['intent'],'ANALYZE_TICKETS')
        self.assertEqual(v['analytics_view'],'SUBCATEGORY_RANKING')
        self.assertEqual(v['analytics_category'],'Application')
        self.assertEqual(v['analytics_limit'],10)

    def test_it_summary(self):
        for phrase in ('give me summary of IT Department','give me an overview of the IT Department'):
            v=self.agent.understand_request(phrase)
            self.assertEqual(v['intent'],'ANALYZE_TICKETS')
            self.assertEqual(v['analytics_view'],'OVERVIEW')

    def test_create_admin_department(self):
        v=self.agent.understand_request('raise a admin ticket')
        self.assertEqual(v['intent'],'CREATE_TICKET')
        self.assertEqual(v['department'],'Admin')
        self.assertIsNone(v['description'])

    def test_problem_ticket_assignee(self):
        v=self.agent.understand_request('who is assigned to PRB-00018?')
        self.assertEqual(v['intent'],'CHECK_TICKET_STATUS')
        self.assertEqual(v['ticket_number'],'PRB-00018')
        self.assertEqual(v['ticket_query'],'ASSIGNED_TO')

    def test_hindi_hinglish_my_tickets(self):
        for phrase in ('मेरे टिकट दिखाओ','mera ticket dikhao'):
            v=self.agent.understand_request(phrase)
            self.assertEqual(v['intent'],'SEARCH_TICKETS')
            self.assertEqual(v['search_scope'],'MY_TICKETS')

    def test_hinglish_create_admin(self):
        v=self.agent.understand_request('admin ticket banao')
        self.assertEqual(v['intent'],'CREATE_TICKET')
        self.assertEqual(v['department'],'Admin')

    def test_does_not_create_just_from_ticket_number(self):
        v=self.agent.understand_request('Check PRB-00018 status')
        self.assertEqual(v['intent'],'CHECK_TICKET_STATUS')
