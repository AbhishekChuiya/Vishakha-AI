import unittest
from ai.agent.input_safety import meaningful_description

class TestInputSafety(unittest.TestCase):
    def test_generic_not_description(self):
        for s in ("Create a ticket", "Create an IT ticket", "Raise a ticket", "Create a ticket for HR", "Please create a service request", ""):
            with self.subTest(s=s):
                self.assertIsNone(meaningful_description(s))
    def test_preserves_actual_description(self):
        for s in ("My laptop won't turn on", "Create a ticket for laptop repair", "I need two blue pens"):
            with self.subTest(s=s):
                self.assertEqual(meaningful_description(s), s)

if __name__ == '__main__':
    unittest.main()
