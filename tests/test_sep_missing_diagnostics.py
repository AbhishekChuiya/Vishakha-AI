import unittest
from tools.diagnose_sep_missing import normalize,rank_candidates,check_routing

class DiagnoseTests(unittest.TestCase):
    def test_alias_and_case(self):
        self.assertEqual(normalize('Feedback & Grievances'),normalize('feedback and grievances'))
    def test_candidates_are_suggestions_only(self):
        out=rank_candidates('Business Cards', [{'name':'Stationery'},{'name':'Business Card Printing'}],limit=1)
        self.assertEqual(out[0]['name'],'Business Card Printing')
    def test_route_conflict(self):
        records=[{'Department':'Admin','Ticket Type':'Service Request','Location':'HO','Group Name':'A','Group ID':4,'Ticket Id':11}, {'Department':'Admin','Ticket Type':'Service Request','Location':'HO','Group Name':'B','Group ID':5,'Ticket Id':11}]
        self.assertEqual(check_routing(records)[0][3],'CONFLICT')

if __name__=='__main__':unittest.main()
