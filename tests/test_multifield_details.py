import pathlib
import unittest
from ai.agent.multifield_details import extract_ticket_details

LOCATIONS = [
    'Ahmedabad Plant (Polyfab-Vadsar)', 'HO Shantigram',
    'Mundra VGPL 1', 'Mundra VGPL 2', 'Mundra VMPL 1', 'Mundra VMPL 2'
]

class MultiFieldDetailsTests(unittest.TestCase):
    def test_issue_location_priority(self):
        result = extract_ticket_details('My laptop screen is not working at Ahmedabad Plant. High priority.', LOCATIONS)
        self.assertEqual(result['location'], LOCATIONS[0])
        self.assertEqual(result['priority'], 'High')
        self.assertEqual(result['remaining_text'], 'My laptop screen is not working')

    def test_ambiguous_location_stays_unfilled(self):
        result = extract_ticket_details('Network issue at Mundra, high priority', LOCATIONS)
        self.assertNotIn('location', result)
        self.assertEqual(result['priority'], 'High')

    def test_exact_location_and_low_priority(self):
        result = extract_ticket_details('Printer issue at HO Shantigram priority: Low', LOCATIONS)
        self.assertEqual(result['location'], 'HO Shantigram')
        self.assertEqual(result['priority'], 'Low')

    def test_no_inferred_values_for_generic_creation(self):
        result = extract_ticket_details('Create a ticket', LOCATIONS)
        self.assertNotIn('location', result)
        self.assertNotIn('priority', result)

    def test_backend_only_changes_create_path(self):
        workflow = (pathlib.Path(__file__).resolve().parents[1] / 'ai/agent/workflow.py').read_text()
        self.assertIn('if self.state.intent == "CREATE_TICKET":\n            details = extract_ticket_details', workflow)
        self.assertIn('return self.handle_option(details[field])', workflow)

if __name__ == '__main__':
    unittest.main()
