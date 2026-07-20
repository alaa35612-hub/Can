from __future__ import annotations
import importlib.util,tempfile,unittest
from pathlib import Path

P=Path(__file__).resolve().parents[1]/'build_symbol_profiles.py'
S=importlib.util.spec_from_file_location('profiles',P);M=importlib.util.module_from_spec(S);assert S and S.loader;S.loader.exec_module(M)

class ProfileTests(unittest.TestCase):
    def test_quantile(self):
        self.assertEqual(M.q([1,2,3],.5),2)
    def test_campaigns_split_after_failure(self):
        rows=[
            {'from_state':'LATENT','to_state':'EARLY_BUILD','adversarial_status':'PASS'},
            {'from_state':'EARLY_BUILD','to_state':'FAILURE','adversarial_status':'PASS'},
            {'from_state':'FAILURE','to_state':'EARLY_BUILD','adversarial_status':'PASS'},
        ]
        self.assertEqual(len(M.campaign_groups(rows)),2)
    def test_reset_is_boundary(self):
        rows=[
            {'from_state':'LATENT','to_state':'EARLY_BUILD'},
            {'from_state':'UNOBSERVED_GAP','to_state':'RESET'},
            {'from_state':'LATENT','to_state':'EARLY_BUILD'},
        ]
        self.assertEqual(len(M.campaign_groups(rows)),2)

if __name__=='__main__':unittest.main()
