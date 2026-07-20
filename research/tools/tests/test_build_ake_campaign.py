from __future__ import annotations

import importlib.util, sys, unittest
from pathlib import Path

P=Path(__file__).resolve().parents[1]/"build_ake_campaign.py"
S=importlib.util.spec_from_file_location("ake_campaign",P)
M=importlib.util.module_from_spec(S); assert S and S.loader
sys.modules["ake_campaign"]=M; S.loader.exec_module(M)


class TestAKECampaign(unittest.TestCase):
    def test_robust_z_detects_relative_extreme(self):
        h=[1.0,1.1,.9,1.05,.95]*5
        self.assertGreater(M.rz(5.0,h),5)

    def test_dedupe_preserves_material_conflict(self):
        a={"timeframe":"15m","timestamp":1,"source":"a.csv","close":1.0,"oi":10.0}
        b={"timeframe":"15m","timestamp":1,"source":"b.csv","close":1.2,"oi":10.0}
        rows,conflicts=M.dedupe([a,b])
        self.assertEqual(len(rows),1)
        self.assertEqual(len(conflicts),1)

    def test_higher_timeframe_hidden_until_close(self):
        rows=[{"timeframe":"1h","timestamp":0,"close_time":3599999},{"timeframe":"1h","timestamp":3600000,"close_time":7199999}]
        self.assertEqual(M.latest_closed(rows,"1h",4000000)["timestamp"],0)

    def test_control_limit(self):
        rows=[]
        for i in range(50):
            rows.append({"timeframe":"15m","timestamp":i*900000,"number_of_trades_rz":.1,"quote_volume_rz":.1,"price_abs_rz":.1})
        self.assertLessEqual(len(M.controls(rows,[])),5)


if __name__=="__main__":unittest.main()
