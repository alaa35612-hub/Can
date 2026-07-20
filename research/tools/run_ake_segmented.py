from __future__ import annotations

import argparse, importlib.util, json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location("ake_base",HERE/"build_ake_campaign.py")
BASE=importlib.util.module_from_spec(SPEC); assert SPEC and SPEC.loader
sys.modules["ake_base"]=BASE; SPEC.loader.exec_module(BASE)


def split_primary(rows,gap_multiple=4):
    p=sorted((r for r in rows if r["timeframe"]=="15m"),key=lambda r:r["timestamp"])
    if not p:return []
    groups=[[p[0]]]
    for r in p[1:]:
        if r["timestamp"]-groups[-1][-1]["timestamp"]>gap_multiple*BASE.TF_MS["15m"]:groups.append([])
        groups[-1].append(r)
    return groups


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,default=Path("."));ap.add_argument("--output-dir",type=Path,default=Path("research/case_studies/AKEUSDT/generated"));a=ap.parse_args()
    sources,raw=BASE.load(a.root); merged,conflicts=BASE.dedupe(raw); rows=BASE.features(merged)
    higher=[r for r in rows if r["timeframe"]!="15m"]
    groups=split_primary(rows); combined=[]
    for n,g in enumerate(groups,1):
        seg=sorted(higher+g,key=lambda r:(r["timestamp"],BASE.TF_MS[r["timeframe"]]))
        led=BASE.ledger(seg)
        if combined and g:
            combined.append({"campaign_id":None,"timestamp":g[0]["timestamp"],"time":BASE.datetime.fromtimestamp(g[0]["timestamp"]/1000,tz=BASE.timezone.utc).isoformat(),"from_state":"UNOBSERVED_GAP","to_state":"RESET","facts_added":["data_gap_campaign_boundary"],"rationale":["primary 15m observations were unavailable for more than four expected intervals"],"supporting_score":0,"opposing_score":0,"dominant_hypothesis":"New campaign must be reconstructed independently","alternative_hypotheses":["Continuation cannot be verified across missing interval"],"higher_timeframes_visible":{},"cutoff_frozen":True})
        for x in led:
            x["segment_id"]=n
            if x.get("campaign_id"):x["campaign_id"]+=f"-S{n}"
        combined.extend(led)
    ctrl=BASE.controls(rows,combined); BASE.write(a.output_dir,sources,rows,conflicts,combined,ctrl)
    summary={"sources":len(sources),"causal_rows":len(rows),"segments":len(groups),"transitions":len(combined),"controls":len(ctrl),"source_conflicts":len(conflicts)}
    (a.output_dir/"AKE_RUN_SUMMARY.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary))

if __name__=="__main__":main()
