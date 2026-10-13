"""Run with: python -m unittest discover -s tests -p test_sep_subcategory_alias.py"""
import unittest
from unittest.mock import Mock, patch
from integrations.ticketing.client import TicketingClient

class LookupTests(unittest.TestCase):
    def setUp(self):
        self.client = TicketingClient.__new__(TicketingClient)
        self.client.base_url = 'https://example.invalid'
        self.client.pat = 'dummy'

    @patch('integrations.ticketing.client.requests.get')
    def test_and_ampersand_fallback(self, get):
        search = Mock(); search.raise_for_status.return_value=None
        search.json.return_value={'content': [], 'totalPages': 0}
        all_items = Mock(); all_items.raise_for_status.return_value=None
        all_items.json.return_value={'content': [
            {'id':21,'name':'Feedback & Grievances'},
            {'id':19,'name':'Meal Booking (VIP & Special guest)'}], 'totalPages':1}
        get.side_effect = [search, all_items]
        result = self.client.get_subcategory(15, 'Feedback and Grievances')
        self.assertEqual(result['id'],21)
        self.assertEqual(get.call_args.kwargs['params']['categoryId'],15)
        self.assertNotIn('search', get.call_args.kwargs['params'])

    @patch('integrations.ticketing.client.requests.get')
    def test_no_near_match(self, get):
        search=Mock(); search.raise_for_status.return_value=None
        search.json.return_value={'content':[], 'totalPages':0}
        listing=Mock(); listing.raise_for_status.return_value=None
        listing.json.return_value={'content':[{'id':19,'name':'Meal Booking (VIP & Special guest)'}], 'totalPages':1}
        get.side_effect=[search, listing]
        with self.assertRaisesRegex(ValueError,'was not found'):
            self.client.get_subcategory(15,'Feedback and Grievances')

    @patch('integrations.ticketing.client.requests.get')
    def test_exact_search_remains(self, get):
        response=Mock(); response.raise_for_status.return_value=None
        response.json.return_value={'content':[{'id':21,'name':'Feedback and Grievances'}]}
        get.return_value=response
        self.assertEqual(self.client.get_subcategory(15,'Feedback and Grievances')['id'],21)
        self.assertEqual(get.call_count,1)

if __name__=='__main__': unittest.main()
