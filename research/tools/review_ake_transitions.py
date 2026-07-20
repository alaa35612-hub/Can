from __future__ import annotations

import argparse, csv, json
from pathlib import Path


def load_timeline(path):
    with path.open(encoding="utf-8",newline="") as f:
        return {int(float(r["timestamp"])):r for r in csv.DictReader(f) if r.get("timeframe")=="15m"}


def f(v):
    try:return float(v)
    except (TypeError,ValueError):return None


def review(item,row):
    status="PASS"; reasons=[]; to=item.get("to_state"); facts=set(item.get("facts_added") or [])
    negative="negative_price_dislocation" in facts
    if to=="ACCEPTED_IGNITION" and negative:
        status="REJECT";reasons.append("acceptance cannot be confirmed on an abnormal negative-price-dislocation candle")
    if to=="EXPANSION":
        current_support=item.get("supporting_score",0)
        if current_support<2:
            status="REJECT";reasons.append("expansion lacks two independent current-cutoff supports")
        if negative:
            status="REJECT";reasons.append("expansion conflicts with abnormal negative price response")
    if to=="CONTINUATION_RELOAD" and negative:
        status="RESTRICT";reasons.append("continuation remains possible but negative price dislocation prevents full confirmation")
    if to in {"EARLY_BUILD","CONFIRMED_BUILD"} and negative:
        status="RESTRICT";reasons.append("fuel/build evidence exists, but direction remains unresolved under negative price response")
    if to=="ACCEPTED_IGNITION" and not ({"execution_expansion","execution_shock","oi_expansion","positive_price_release"}&facts):
        status="RESTRICT" if status=="PASS" else status;reasons.append("acceptance is based mainly on retention and needs independent execution/fuel confirmation")
    if not reasons:reasons.append("no adversarial rejection condition triggered")
    out=dict(item);out["adversarial_status"]=status;out["adversarial_reasons"]=reasons
    out["contemporary_close"]=f(row.get("close")) if row else None
    out["contemporary_price_change_pct"]=f(row.get("price_change_pct")) if row else None
    return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--directory",type=Path,default=Path("research/case_studies/AKEUSDT/generated"));a=ap.parse_args()
    ledger=json.loads((a.directory/"AKE_STATE_LEDGER.json").read_text(encoding="utf-8"));timeline=load_timeline(a.directory/"AKE_CAUSAL_TIMELINE.csv")
    reviewed=[review(x,timeline.get(int(x["timestamp"]))) for x in ledger]
    (a.directory/"AKE_REVIEWED_STATE_LEDGER.json").write_text(json.dumps(reviewed,indent=2),encoding="utf-8")
    counts={s:sum(x["adversarial_status"]==s for x in reviewed) for s in ("PASS","RESTRICT","REJECT")}
    rows="\n".join(f"| {x['time']} | {x['from_state']} → {x['to_state']} | {x['adversarial_status']} | {'; '.join(x['adversarial_reasons'])} |" for x in reviewed)
    text=f"""# AKEUSDT Adversarial Transition Review

The automated ledger proposes transitions; this file evaluates whether each transition survives explicit contradiction checks. `REJECT` transitions must not be used as facts. `RESTRICT` transitions remain hypotheses with capped confidence.

## Counts

- PASS: {counts['PASS']}
- RESTRICT: {counts['RESTRICT']}
- REJECT: {counts['REJECT']}

## Review table

| Cutoff | Candidate transition | Status | Reason |
|---|---|---|---|
{rows}

## Interpretation

The raw State Ledger is an algorithmic proposal. The reviewed ledger is the valid research interface. A later transition depending on a rejected predecessor must be re-evaluated during the next campaign pass rather than inherited automatically.
"""
    (a.directory/"AKE_ADVERSARIAL_REVIEW.md").write_text(text,encoding="utf-8")
    (a.directory/"AKE_REVIEW_SUMMARY.json").write_text(json.dumps(counts,indent=2),encoding="utf-8")
    print(json.dumps(counts))

if __name__=="__main__":main()
