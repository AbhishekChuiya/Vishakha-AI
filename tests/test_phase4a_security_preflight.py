import tempfile
from pathlib import Path
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from check_production_readiness import inspect

class SecurityPreflightTests(unittest.TestCase):
    def test_flags_debug_and_literal_secret_without_printing_secret(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'config').mkdir(); (p/'config/settings.py').write_text("DEBUG = True\nSECRET_KEY = 'do-not-disclose'\n")
            items=inspect(p)
            self.assertIn('DEBUG_ON', {x['code'] for x in items})
            self.assertIn('HARDCODED_SECRET_KEY', {x['code'] for x in items})
            self.assertNotIn('do-not-disclose', str(items))
    def test_flags_csrf_exempt(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'apps/assistant').mkdir(parents=True); (p/'apps/assistant/views.py').write_text('@csrf_exempt\ndef endpoint(request): pass\n')
            self.assertIn('CSRF_EXEMPT_POST',{x['code'] for x in inspect(p)})
    def test_no_secret_in_finding(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'config').mkdir(); (p/'config/settings.py').write_text("SECRET_KEY='super-secret-value'\n")
            self.assertNotIn('super-secret-value',str(inspect(p)))

if __name__ == '__main__': unittest.main()
