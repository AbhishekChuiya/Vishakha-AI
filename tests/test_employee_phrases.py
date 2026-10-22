"""Run: python -m unittest discover -s tests -p test_employee_phrases.py"""
import importlib.util
import pathlib
import unittest

FILE = pathlib.Path(__file__).resolve().parents[1] / 'ai' / 'agent' / 'employee_phrases.py'
spec = importlib.util.spec_from_file_location('employee_phrases_under_test', FILE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
classify = module.classify_employee_shorthand


class PhraseTests(unittest.TestCase):
    def test_my_tickets(self):
        for phrase in ('Mera ticket', 'mere ticket dikhao', 'मेरे टिकट दिखाओ', 'my tikket', 'mujhe ticket dikhao'):
            with self.subTest(phrase=phrase):
                self.assertEqual(classify(phrase)['intent'], 'SEARCH_TICKETS')
                self.assertEqual(classify(phrase)['search_scope'], 'MY_TICKETS')

    def test_it_incidents(self):
        for phrase in ('Laptop kharab hai', 'laptp khrab hai', 'Network nahi chal raha', 'wifi down', 'लैपटॉप खराब है', 'printer not working', 'keyboard issue'):
            with self.subTest(phrase=phrase):
                obj = classify(phrase)
                self.assertEqual(obj['intent'], 'CREATE_TICKET')
                self.assertEqual(obj['department'], 'IT Department')
                for name in ('category', 'request_type', 'priority', 'location'):
                    self.assertIsNone(obj[name])

    def test_conservative(self):
        for phrase in ('leave chahiye kal', 'छुट्टी चाहिए', 'please explain laptops', 'hello', 'ticket create hua?', 'show laptop issue ticket'):
            with self.subTest(phrase=phrase):
                self.assertIsNone(classify(phrase))

    def test_ambiguous_create(self):
        for phrase in ('create a ticket', 'ticket banao', 'टिकट बनाओ'):
            with self.subTest(phrase=phrase):
                obj = classify(phrase)
                self.assertEqual(obj['intent'], 'CREATE_TICKET')
                self.assertIsNone(obj['department'])

    def test_ticket_count_and_status(self):
        self.assertTrue(classify('mere kitne ticket hain')['ticket_count_only'])
        self.assertEqual(classify('my open tickets')['ticket_status_filter'], 'OPEN')

if __name__ == '__main__':
    unittest.main()
