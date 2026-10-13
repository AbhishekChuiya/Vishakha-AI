import unittest
from tools.audit_sep_resolver_groups import check_rows

class ResolverAuditTests(unittest.TestCase):
    def record(self, dept, group, gid):
        return {'Department':dept,'Ticket Type':'Service Request','Location':'HO Shantigram','Group Name':group,'Group ID':gid,'Ticket Id':'11'}
    def test_admin_ambiguity_is_flagged(self):
        result=check_rows([self.record('Admin','Admin - HO - SR','16'),self.record('Admin','Admin_HO_SR','61')])
        self.assertEqual(sum(x['status']=='AMBIGUOUS_ROUTING_KEY' for x in result),2)
    def test_it_specialists_not_auto_selected(self):
        a=self.record('IT Department','SAP BASIS SR','32'); a['Location']='All'
        b=self.record('IT Department','SAP MM SR','37'); b['Location']='All'
        result=check_rows([a,b])
        self.assertEqual(sum(x['status']=='SPECIALIST_GROUP_SELECTION_REQUIRED' for x in result),2)
    def test_export_validation(self):
        result=check_rows([self.record('Admin','Admin_HO_SR','61')],{'61':'Admin_HO_SR'})
        self.assertEqual(result[0]['status'],'SEP_VERIFIED_FROM_EXPORT')
    def test_no_live_claim_without_export(self):
        self.assertEqual(check_rows([self.record('Admin','Admin_HO_SR','61')]),[])

if __name__=='__main__': unittest.main()
