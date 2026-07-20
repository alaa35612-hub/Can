from __future__ import annotations
import importlib.util,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'analyze_tlm_acceptance_discriminators.py';s=importlib.util.spec_from_file_location('m',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def row(t,close,oi,pc,oc,rank):
    return {'timestamp':t,'close_time':t+m.STEP-1,'close':close,'oi':oi,'price_change_pct':pc,'oi_change_pct':oc,'number_of_trades_rank':rank,'quote_volume_rank':rank,'execution_rank':rank,'taker_quote_imbalance_pct':10.0}

class Tests(unittest.TestCase):
    def test_cutoff_excludes_future(self):
        r=[row(0,100,1000,1,1,.9),row(m.STEP,102,1010,2,1,.8),row(2*m.STEP,150,1300,47,28,1)]
        x=m.metrics(r,0,15);self.assertEqual(x['rows_visible'],2);self.assertAlmostEqual(x['price_return_pct'],2);self.assertAlmostEqual(x['oi_return_pct'],1)
    def test_gap_abstains(self):
        x=m.metrics([row(0,100,1000,1,1,.9),row(2*m.STEP,102,1010,2,1,.8)],0,30);self.assertEqual(x['coverage_status'],'OBSERVATION_GAP');self.assertTrue(m.assess(x,{'medians':{},'counts':{}})['assessment_status'].startswith('ABSTAIN_'))
    def test_baseline_is_strictly_prior(self):
        h=[{'campaign_index':1,'ignition_timestamp':100,'checkpoint_minutes':30,'coverage_status':'COMPLETE','price_return_pct':1},{'campaign_index':2,'ignition_timestamp':200,'checkpoint_minutes':30,'coverage_status':'COMPLETE','price_return_pct':2},{'campaign_index':3,'ignition_timestamp':300,'checkpoint_minutes':30,'coverage_status':'COMPLETE','price_return_pct':99}]
        b=m.baseline(h,300,30);self.assertEqual(b['prior_campaign_indices'],[1,2]);self.assertEqual(b['medians']['price_return_pct'],1.5)
    def test_fuel_retention(self):
        x={'coverage_status':'COMPLETE','checkpoint_minutes':30,'price_return_pct':3,'oi_return_pct':2,'execution_rank_median':.8,'execution_decay':-.1}
        b={'medians':{k:0 for k in m.METRICS},'counts':{k:3 for k in m.METRICS}};b['medians']['execution_rank_median']=.7
        self.assertEqual(m.assess(x,b)['dominant_hypothesis'],'TLM_POST_IGNITION_FUEL_RETENTION')
    def test_short_covering(self):
        x={'coverage_status':'COMPLETE','checkpoint_minutes':30,'price_return_pct':2,'oi_return_pct':-1,'execution_rank_median':.4,'execution_decay':-.3}
        b={'medians':{k:.5 for k in m.METRICS},'counts':{k:3 for k in m.METRICS}};b['medians']['price_return_pct']=3;b['medians']['oi_return_pct']=0
        self.assertEqual(m.assess(x,b)['dominant_hypothesis'],'TLM_SHORT_COVERING_ONLY')
    def test_outcome_reveal_is_separate(self):
        r=[row(i*m.STEP,100+i,1000+i,1,.1,.8) for i in range(6)];a=[{'campaign_index':1,'outcome':'accepted_expansion','ignition_timestamp':0,'ignition_time':m.ms_iso(0),'valid_ignition':True,'ignition_review_status':'PASS','acceptance_timestamp':m.STEP,'expansion_timestamp':2*m.STEP,'failure_timestamp':None,'rejected_transition_count':0,'rejected_states':[],'rejection_reasons':[]}]
        frozen,trace=m.freeze(r,a);self.assertTrue(all(x['outcome_hidden'] for x in frozen));self.assertEqual(trace[-1]['record_type'],'OUTCOME_REVEALED_AFTER_ALL_CHECKPOINTS');self.assertFalse(trace[-1]['historical_assessment_rewritten'])
    def test_matrix_uses_campaign_unit(self):
        aa=[{'campaign_index':1,'outcome':'accepted_expansion'},{'campaign_index':2,'outcome':'accepted_expansion'},{'campaign_index':3,'outcome':'failed_ignition'},{'campaign_index':4,'outcome':'failed_ignition'}];f=[]
        for i,v in ((1,5),(2,6),(3,-1),(4,-2)):f.append({'campaign_index':i,'checkpoint_minutes':30,'valid_ignition':True,'metrics':{'coverage_status':'COMPLETE','price_return_pct':v}})
        r=next(x for x in m.matrix(f,aa) if x['checkpoint_minutes']==30 and x['metric']=='price_return_pct');self.assertEqual(r['success_count'],2);self.assertEqual(r['failure_count'],2);self.assertEqual(r['observed_range_status'],'NON_OVERLAPPING_SUCCESS_ABOVE_FAILURE');self.assertEqual(r['cliff_delta'],1)

if __name__=='__main__':unittest.main()
