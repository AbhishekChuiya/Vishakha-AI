"""Run: python manage.py test apps.assistant.test_sep_submission"""
from unittest.mock import Mock
from django.contrib.auth import get_user_model
from django.test import TestCase
from .models import ChatConversation, SepTicketSubmission
from .views import _confirm_sep_ticket_once

class SepSubmissionTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username='sep_guard_test', password='Example123!')
        self.chat = ChatConversation.objects.create(user=user, chat_id='sep_guard_case', application='ticketing')
        self.workflow = Mock()
        self.workflow.state.description = 'Internet connectivity is interrupted on floor 2'
        self.workflow.state.is_complete.return_value = True
        self.workflow.state.to_dict.return_value = {'description':'Internet connectivity is interrupted on floor 2','location':'Mundra'}
        self.workflow.confirm_ticket.return_value = {'type':'success','ticket_number':'INC-TEST-1','message':'Ticket created successfully.'}

    def test_double_submit_calls_sep_once(self):
        first = _confirm_sep_ticket_once(self.chat, self.workflow)
        second = _confirm_sep_ticket_once(self.chat, self.workflow)
        self.assertEqual(first['ticket_number'], second['ticket_number'])
        self.assertEqual(self.workflow.confirm_ticket.call_count, 1)
        self.assertEqual(SepTicketSubmission.objects.count(), 1)

    def test_uncertain_response_is_not_retried(self):
        self.workflow.confirm_ticket.return_value = {'type':'error','message':'Timeout'}
        first = _confirm_sep_ticket_once(self.chat, self.workflow)
        second = _confirm_sep_ticket_once(self.chat, self.workflow)
        self.assertIn('Check My Tickets', first['message'])
        self.assertIn('Check My Tickets', second['message'])
        self.assertEqual(self.workflow.confirm_ticket.call_count, 1)

    def test_missing_subcategory_does_not_consume_submission(self):
        self.workflow.confirm_ticket.return_value = {
            "type": "error",
            "message": "I couldn't create the ticket in the Service Excellence Portal.",
            "details": "Exact subcategories match not found for 'Feedback and Grievances'. API returned: []",
            "options": ["Confirm & Create Ticket", "Cancel"],
        }
        result = _confirm_sep_ticket_once(self.chat, self.workflow)
        self.assertEqual(result["type"], "error")
        self.assertIn("No ticket was submitted", result["message"])
        self.assertIn("Confirm & Create Ticket", result["options"])
        self.assertEqual(SepTicketSubmission.objects.count(), 0)
        _confirm_sep_ticket_once(self.chat, self.workflow)
        self.assertEqual(self.workflow.confirm_ticket.call_count, 2)
