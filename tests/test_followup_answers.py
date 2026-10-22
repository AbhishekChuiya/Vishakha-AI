import unittest
from ai.agent.followup_answers import normalize_pending_answer as norm

SITES = ["Ahmedabad Plant (Polyfab-Vadsar)", "HO Shantigram", "Mundra VGPL 1", "Mundra VMPL 1"]

class FollowupAnswersTests(unittest.TestCase):
    def test_priority_phrases(self):
        self.assertEqual(norm('priority', 'High priority'), 'High')
        self.assertEqual(norm('priority', 'low'), 'Low')
        self.assertEqual(norm('priority', 'please set high priority'), 'High')
        self.assertEqual(norm('priority', 'higher than medium'), 'higher than medium')

    def test_location_unique_and_ambiguous(self):
        self.assertEqual(norm('location', 'Ahmedabad plant', locations=SITES), SITES[0])
        self.assertEqual(norm('location', 'HO Shantigram', locations=SITES), SITES[1])
        self.assertEqual(norm('location', 'Mundra', locations=SITES), 'Mundra')

    def test_request_type_and_department(self):
        self.assertEqual(norm('request_type', 'incident', request_types=['Incident Request','Service Request']), 'Incident Request')
        self.assertEqual(norm('request_type', 'incident', request_types=['Service Request']), 'incident')
        self.assertEqual(norm('department', 'it', departments=['IT Department','Admin']), 'IT Department')

    def test_category_exact_only(self):
        self.assertEqual(norm('category', 'hardware', categories=['Hardware','Application']), 'Hardware')
        self.assertEqual(norm('category', 'hard', categories=['Hardware','Application']), 'hard')

    def test_unrelated_fields_not_transformed(self):
        self.assertEqual(norm('description', 'Screen problem'), 'Screen problem')
        self.assertEqual(norm('confirmation', 'Confirm & Create Ticket'), 'Confirm & Create Ticket')

if __name__ == '__main__':
    unittest.main()
