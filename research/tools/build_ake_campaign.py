from __future__ import annotations

import argparse, csv, json, math, statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

TF_MS={"5m":300000,"15m":900000,"1h":3600000,"4h":14400000,"1d":86400000}
FIELDS=("close","rsi","number_of_trades","quote_volume","avg_quote_per_trade","taker_quote_imbalance_pct","oi","oi_value","acco_ls_ratio","posit_ls_ratio","global_ls_ratio","funding_rate")


def num(v):
    try:
        x=float(v); return x if math.isfinite(x) else None
    except (TypeError,ValueError): return None


def tf_of(p):
    return next((t for t in TF_MS if f"_{t}_" in p.name),None)


def load(root):
    rows=[]; sources=[]
    for p in sorted(root.glob("AKEUSDT_*_enriched_candles.csv")):
        tf=tf_of(p)
        if not tf: continue
        sources.append(p.name)
        with p.open(encoding="utf-8-sig",newline="") as f:
            for x in csv.DictReader(f):
                if x.get("symbol")!="AKEUSDT" or str(x.get("is_closed_candle","")).lower() not in {"true","1"}: continue
                ts=int(float(x.get("timestamp") or x.get("open_time") or 0))
                row={"timestamp":ts,"close_time":int(float(x.get("close_time") or ts+TF_MS[tf]-1)),"timeframe":tf,"source":p.name}
                row.update({k:num(x.get(k)) for k in FIELDS}); rows.append(row)
    return sources,rows


def dedupe(rows):
    groups=defaultdict(list)
    for r in rows: groups[(r["timeframe"],r["timestamp"])].append(r)
    out=[]; conflicts=[]
    for key,g in groups.items():
        g.sort(key=lambda r:(sum(v is not None for v in r.values()),r["source"]),reverse=True); chosen=g[0]; out.append(chosen)
        bad=[]
        for other in g[1:]:
            fields=[]
            for k in FIELDS:
                a,b=chosen.get(k),other.get(k)
                if a is None or b is None: continue
                if abs(a-b)/max(abs(a),abs(b),1e-12)>1e-8: fields.append(k)
            if fields: bad.append({"source":other["source"],"fields":fields})
        if bad: conflicts.append({"timeframe":key[0],"timestamp":key[1],"chosen":chosen["source"],"conflicts":bad})
    return sorted(out,key=lambda r:(r["timeframe"],r["timestamp"])),conflicts


def rz(v,h,min_n=20):
    if v is None or len(h)<min_n:return None
    med=statistics.median(h); mad=statistics.median(abs(x-med) for x in h)
    if mad<1e-15:return 0.0 if v==med else math.copysign(10,v-med)
    return .67448975*(v-med)/mad


def pct(a,b):
    return None if a is None or b in (None,0) else (a/b-1)*100


def features(rows):
    by=defaultdict(list)
    for r in rows:by[r["timeframe"]].append(r)
    out=[]
    for tf,seq in by.items():
        seq.sort(key=lambda r:r["timestamp"]); hist=defaultdict(list); prev=None
        for r in seq:
            x=dict(r)
            x["price_change_pct"]=pct(x["close"],prev["close"] if prev else None)
            x["oi_change_pct"]=pct(x["oi"],prev["oi"] if prev else None)
            for k in ("number_of_trades","quote_volume","oi","oi_value","avg_quote_per_trade"):x[k+"_rz"]=rz(x[k],hist[k])
            x["price_abs_rz"]=rz(abs(x["price_change_pct"]) if x["price_change_pct"] is not None else None,hist["absret"])
            out.append(x)
            for k in ("number_of_trades","quote_volume","oi","oi_value","avg_quote_per_trade"):
                if x[k] is not None:hist[k].append(x[k])
            if x["price_change_pct"] is not None:hist["absret"].append(abs(x["price_change_pct"]))
            prev=x
    return sorted(out,key=lambda r:(r["timestamp"],TF_MS[r["timeframe"]]))


def latest_closed(rows,tf,cutoff):
    x=[r for r in rows if r["timeframe"]==tf and r["close_time"]<=cutoff]
    return x[-1] if x else None


def ledger(rows):
    p=[r for r in rows if r["timeframe"]=="15m"]
    state="LATENT"; cid=None; support=oppose=0; out=[]
    for i,r in enumerate(p):
        ex=max([z for z in (r.get("number_of_trades_rz"),r.get("quote_volume_rz")) if z is not None],default=None)
        shock=ex is not None and ex>=5; active=ex is not None and ex>=2.5
        abnormal=r.get("price_abs_rz") is not None and r["price_abs_rz"]>=2.5
        ret=r.get("price_change_pct") or 0; oi_delta=r.get("oi_change_pct")
        oi_up=oi_delta is not None and oi_delta>0 and (r.get("oi_rz") is None or r["oi_rz"]>=1.5)
        oi_down=oi_delta is not None and oi_delta<0 and r.get("oi_rz") is not None and r["oi_rz"]<=-2.5
        positive=ret>0 and (r.get("taker_quote_imbalance_pct") is None or r["taker_quote_imbalance_pct"]>-20)
        negative=ret<0 and (r.get("taker_quote_imbalance_pct") is None or r["taker_quote_imbalance_pct"]<20)
        higher={t:latest_closed(rows,t,r["close_time"]) for t in ("1h","4h","1d")}
        hs=sum(1 for x in higher.values() if x and (x.get("price_change_pct") or 0)>0); ho=sum(1 for x in higher.values() if x and (x.get("price_change_pct") or 0)<0)
        pos=int(active)+int(oi_up)+int(abnormal and positive)+int(hs>=2); neg=int(oi_down)+int(abnormal and negative)+int(ho>=2)
        support=support+1 if pos>=2 else max(0,support-1); oppose=oppose+1 if neg>=2 else max(0,oppose-1)
        facts=[]
        if shock:facts.append("execution_shock")
        elif active:facts.append("execution_expansion")
        if oi_up:facts.append("oi_expansion")
        if oi_down:facts.append("oi_contraction")
        if abnormal and positive:facts.append("positive_price_release")
        if abnormal and negative:facts.append("negative_price_dislocation")
        if hs>=2:facts.append("higher_timeframe_support")
        if ho>=2:facts.append("higher_timeframe_opposition")
        new=state; why=[]
        if state in {"LATENT","FAILURE","RESET"} and ((active and (oi_up or positive)) or (oi_up and not abnormal)):
            new="EARLY_BUILD"; why.append("fuel/execution changed before or with price response")
        if new=="EARLY_BUILD" and support>=2:new="CONFIRMED_BUILD";why.append("persistence across observations")
        if new in {"EARLY_BUILD","CONFIRMED_BUILD"} and shock and positive:new="IGNITION_CANDIDATE";why.append("execution shock with positive response")
        if state=="IGNITION_CANDIDATE" and i:
            prev=p[i-1]
            if (prev.get("price_change_pct") or 0)>0 and r.get("close") and prev.get("close") and r["close"]/prev["close"]>=.94 and not oi_down:
                new="ACCEPTED_IGNITION";why.append("post-release retention without immediate OI collapse")
            elif oppose>=2:new="FAILURE";why.append("persistent opposing evidence")
        if state=="ACCEPTED_IGNITION":
            if support>=2 and positive:new="EXPANSION";why.append("accepted structure continued")
            elif oppose>=2:new="COOLING";why.append("opposition increased")
        if state=="EXPANSION":
            if active and not oi_down:new="CONTINUATION_RELOAD";why.append("execution persisted without fuel collapse")
            elif oppose>=2:new="COOLING";why.append("persistent opposition")
        if state in {"COOLING","CONTINUATION_RELOAD"}:
            if shock and positive and not oi_down:new="CONTINUATION_RELOAD";why.append("fresh execution release")
            elif oppose>=3:new="FAILURE";why.append("opposition exceeded cooling tolerance")
        if new!=state:
            if new=="EARLY_BUILD" and cid is None:cid=f"AKEUSDT-15m-{datetime.fromtimestamp(r['timestamp']/1000,tz=timezone.utc):%Y%m%d-%H%M}"
            hyp="Quiet build" if new in {"EARLY_BUILD","CONFIRMED_BUILD"} else "Execution-led ignition" if new=="IGNITION_CANDIDATE" else "Accepted expansion/continuation" if new in {"ACCEPTED_IGNITION","EXPANSION","CONTINUATION_RELOAD"} else "Cooling versus distribution" if new=="COOLING" else "Failed/exhausted campaign"
            out.append({"campaign_id":cid,"timestamp":r["timestamp"],"time":datetime.fromtimestamp(r["timestamp"]/1000,tz=timezone.utc).isoformat(),"from_state":state,"to_state":new,"facts_added":facts,"rationale":why,"supporting_score":pos,"opposing_score":neg,"dominant_hypothesis":hyp,"alternative_hypotheses":["Short-covering only","Transient event spike","New unidentified structure"],"higher_timeframes_visible":{t:(x["timestamp"] if x else None) for t,x in higher.items()},"cutoff_frozen":True})
            state=new
            if state=="FAILURE":cid=None;support=oppose=0
    return out


def controls(rows,led):
    p=[r for r in rows if r["timeframe"]=="15m"]; ts={x["timestamp"] for x in led}; out=[]
    for i in range(8,len(p)-4):
        if any(abs(p[i]["timestamp"]-t)<=8*TF_MS["15m"] for t in ts):continue
        w=p[i-4:i+5]; ex=max(max(x.get("number_of_trades_rz") or -99,x.get("quote_volume_rz") or -99) for x in w); mv=max(x.get("price_abs_rz") or -99 for x in w)
        if ex<2 and mv<2:out.append({"center_timestamp":p[i]["timestamp"],"center_time":datetime.fromtimestamp(p[i]["timestamp"]/1000,tz=timezone.utc).isoformat(),"window_candles":9,"selection_reason":"ordinary causal window"})
        if len(out)>=5:break
    return out


def write(outdir,sources,rows,conflicts,led,ctrl):
    outdir.mkdir(parents=True,exist_ok=True)
    fields=sorted({k for r in rows for k in r})
    with (outdir/"AKE_CAUSAL_TIMELINE.csv").open("w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    (outdir/"AKE_STATE_LEDGER.json").write_text(json.dumps(led,indent=2),encoding="utf-8")
    (outdir/"AKE_BLIND_REPLAY_TRACE.jsonl").write_text("\n".join(json.dumps(x) for x in led)+"\n",encoding="utf-8")
    (outdir/"AKE_CONTROL_WINDOWS.json").write_text(json.dumps(ctrl,indent=2),encoding="utf-8")
    (outdir/"AKE_SOURCE_CONFLICTS.json").write_text(json.dumps(conflicts,indent=2),encoding="utf-8")
    table="\n".join(f"| {x['time']} | {x['from_state']} | {x['to_state']} | {', '.join(x['facts_added'])} | {x['dominant_hypothesis']} |" for x in led) or "| — | — | — | none | no transition |"
    report=f"""# AKEUSDT Campaign Reconstruction — Causal Pass 1

Primary timeframe is 15m. Higher timeframes are exposed only after close. Baselines use prior rows only through robust median/MAD. JSONL twins are not independent evidence. Pattern names remain hypotheses.

## Sources
"""+"\n".join(f"- `{x}`" for x in sources)+f"""

## Frozen State Ledger transitions

| Cutoff | From | To | Facts | Dominant hypothesis |
|---|---|---|---|---|
{table}

## Controls and limitations

- {len(ctrl)} ordinary same-asset windows were selected outside transition neighborhoods.
- The documented gap between old and new 15m captures remains explicit.
- Daily history is short and cannot provide mature long-horizon baselines.
- Materially conflicting overlapping rows: {len(conflicts)}.
- No rule is promoted to durable status in this pass.
"""
    (outdir/"AKE_CAMPAIGN_RECONSTRUCTION.md").write_text(report,encoding="utf-8")


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,default=Path("."));ap.add_argument("--output-dir",type=Path,default=Path("research/case_studies/AKEUSDT/generated"));a=ap.parse_args()
    sources,raw=load(a.root)
    if not sources:raise SystemExit("No AKE CSV files found")
    merged,conflicts=dedupe(raw);rows=features(merged);led=ledger(rows);ctrl=controls(rows,led);write(a.output_dir,sources,rows,conflicts,led,ctrl)
    print(json.dumps({"sources":len(sources),"causal_rows":len(rows),"transitions":len(led),"controls":len(ctrl),"source_conflicts":len(conflicts)}))

if __name__=="__main__":main()
