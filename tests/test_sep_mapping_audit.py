import unittest
from tools.audit_sep_mappings import norm, candidates

class SafeMatchingTest(unittest.TestCase):
    def test_ampersand(self):
        self.assertEqual(norm('Feedback and Grievances'), norm('Feedback & Grievances'))
    def test_ambiguous(self):
        self.assertEqual(len(candidates('Feedback and Grievances', [{'name':'Feedback & Grievances','id':21}, {'name':'Feedback and Grievances','id':22}])),2)
    def test_unrelated(self):
        self.assertFalse(candidates('Network Failure',[{'name':'Network Connectivity'}]))

if __name__=='__main__':unittest.main()
