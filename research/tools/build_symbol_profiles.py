from __future__ import annotations
import argparse,csv,json,math,statistics
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path

TF_ORDER={'5m':0,'15m':1,'1h':2,'4h':3,'1d':4}

def f(v):
    try:
        x=float(v); return x if math.isfinite(x) else None
    except (TypeError,ValueError): return None

def q(vals,p):
    vals=sorted(x for x in vals if x is not None)
    if not vals:return None
    k=(len(vals)-1)*p; lo=int(k); hi=min(lo+1,len(vals)-1); a=k-lo
    return vals[lo]*(1-a)+vals[hi]*a

def pct(a,b):
    return None if a is None or b in (None,0) else (a/b-1)*100

def dt(ts):return datetime.fromtimestamp(ts/1000,tz=timezone.utc).isoformat()

def load_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as fh:return list(csv.DictReader(fh))

def load_json(path,default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def campaign_groups(reviewed):
    groups=[]; current=[]
    for x in reviewed:
        if x.get('to_state')=='RESET' or x.get('from_state')=='UNOBSERVED_GAP':
            if current:groups.append(current);current=[]
            continue
        if x.get('to_state') in {'EARLY_BUILD','CONFIRMED_BUILD','IGNITION_CANDIDATE'} and x.get('from_state') in {'LATENT','FAILURE','RESET'} and current:
            groups.append(current);current=[]
        current.append(x)
        if x.get('to_state')=='FAILURE':
            groups.append(current);current=[]
    if current:groups.append(current)
    return groups

def profile(symbol,base):
    prefix=symbol.replace('USDT','')
    g=base/symbol/'generated'
    timeline=load_csv(g/f'{prefix}_CAUSAL_TIMELINE.csv')
    reviewed=load_json(g/f'{prefix}_REVIEWED_STATE_LEDGER.json',[])
    summary=load_json(g/f'{prefix}_RUN_SUMMARY.json',{})
    conflicts=load_json(g/f'{prefix}_SOURCE_CONFLICTS.json',[])
    tf=defaultdict(list)
    for r in timeline:tf[r.get('timeframe')].append(r)
    tf_stats={}
    for name,rows in tf.items():
        trades=[f(r.get('number_of_trades')) for r in rows]; quote=[f(r.get('quote_volume')) for r in rows]
        oi=[f(r.get('oi')) for r in rows]; ret=[abs(f(r.get('price_change_pct')) or 0) for r in rows]
        tf_stats[name]={
            'rows':len(rows),'start':dt(int(float(rows[0]['timestamp']))) if rows else None,'end':dt(int(float(rows[-1]['timestamp']))) if rows else None,
            'trades_p50':q(trades,.5),'trades_p90':q(trades,.9),'quote_volume_p50':q(quote,.5),'quote_volume_p90':q(quote,.9),
            'oi_p50':q(oi,.5),'abs_return_p50':q(ret,.5),'abs_return_p90':q(ret,.9)
        }
    primary=sorted(tf.get('15m',[]),key=lambda r:int(float(r['timestamp'])))
    lags=[]
    for i,r in enumerate(primary):
        ex=max(f(r.get('number_of_trades_rank')) or 0,f(r.get('quote_volume_rank')) or 0)
        oi_rank=f(r.get('oi_rank')) or 0
        if ex>=.9 or oi_rank>=.9:
            base_close=f(r.get('close'))
            threshold=q([abs(f(x.get('price_change_pct')) or 0) for x in primary[:i+1]],.9) or 0
            for j in range(i+1,min(i+17,len(primary))):
                move=abs(pct(f(primary[j].get('close')),base_close) or 0)
                if move>=threshold:
                    lags.append((j-i)*15);break
    groups=campaign_groups(reviewed)
    outcomes=[]
    for n,grp in enumerate(groups,1):
        states=[x.get('to_state') for x in grp if x.get('adversarial_status')!='REJECT']
        statuses=Counter(x.get('adversarial_status') for x in grp)
        if 'CONTINUATION_RELOAD' in states or 'EXPANSION' in states: outcome='accepted_expansion'
        elif 'ACCEPTED_IGNITION' in states: outcome='accepted_without_expansion'
        elif 'IGNITION_CANDIDATE' in states and 'FAILURE' in states: outcome='failed_ignition'
        elif 'CONFIRMED_BUILD' in states: outcome='build_without_acceptance'
        else: outcome='unresolved'
        outcomes.append({'campaign_index':n,'start':grp[0].get('time'),'end':grp[-1].get('time'),'states':states,'review_counts':dict(statuses),'outcome':outcome,
                         'dominant_hypotheses':sorted(set(x.get('dominant_hypothesis') for x in grp if x.get('dominant_hypothesis'))),
                         'alternative_hypotheses':sorted(set(h for x in grp for h in (x.get('alternative_hypotheses') or [])))})
    counts=Counter(x['outcome'] for x in outcomes)
    p={'symbol':symbol,'data_scope':summary,'timeframe_profiles':tf_stats,'source_conflicts':len(conflicts),
       'execution_to_price_lag_minutes':{'median':q(lags,.5),'p90':q(lags,.9),'observations':len(lags)},
       'campaign_outcome_counts':dict(counts),'false_ignition_rate':(counts['failed_ignition']/len(outcomes) if outcomes else None),
       'reliable_timeframes':sorted([k for k,v in tf_stats.items() if v['rows']>=100],key=lambda x:TF_ORDER.get(x,99)),
       'limited_timeframes':sorted([k for k,v in tf_stats.items() if v['rows']<100],key=lambda x:TF_ORDER.get(x,99)),
       'structural_notes':[],'unknowns':[],'campaigns':outcomes}
    if len(conflicts)>200:p['structural_notes'].append('High source-conflict burden; source-selection sensitivity is mandatory.')
    elif conflicts:p['structural_notes'].append('Material source conflicts exist and cap confidence.')
    else:p['structural_notes'].append('No material overlap conflicts in the selected source set.')
    if counts['failed_ignition']>0:p['structural_notes'].append('Ignition attempts can fail before acceptance; rejection chains are symbol-relevant.')
    if counts['accepted_expansion']>1:p['structural_notes'].append('Multiple accepted campaigns occur; do not compress history into one campaign.')
    if not tf_stats.get('1d') or tf_stats.get('1d',{}).get('rows',0)<60:p['unknowns'].append('Daily regime maturity is insufficient for durable long-horizon claims.')
    p['unknowns'].append('Observed campaign taxonomy is provisional and may miss symbol-specific unknown structures.')
    return p

def write_profile(p,outroot):
    sym=p['symbol']; d=outroot/sym; d.mkdir(parents=True,exist_ok=True)
    (d/'SYMBOL_STRUCTURAL_PROFILE.json').write_text(json.dumps(p,indent=2),encoding='utf-8')
    tfrows='\n'.join(f"| {k} | {v['rows']} | {v['start']} | {v['end']} | {v['trades_p50']} | {v['trades_p90']} | {v['quote_volume_p50']} | {v['quote_volume_p90']} |" for k,v in sorted(p['timeframe_profiles'].items(),key=lambda kv:TF_ORDER.get(kv[0],99)))
    camps='\n'.join(f"| {x['campaign_index']} | {x['start']} | {x['end']} | {x['outcome']} | {', '.join(x['states'])} |" for x in p['campaigns']) or '| — | — | — | none | none |'
    text=f"""# {sym} Symbol Structural Profile

This profile is symbol-specific. Shared state names are indexing vocabulary, not a mandatory market path.

## Data and reliability

- Source conflicts: {p['source_conflicts']}
- Reliable timeframes: {', '.join(p['reliable_timeframes']) or 'none'}
- Limited timeframes: {', '.join(p['limited_timeframes']) or 'none'}
- Median execution/OI anomaly to material price-response lag: {p['execution_to_price_lag_minutes']['median']} minutes
- Lag observations: {p['execution_to_price_lag_minutes']['observations']}
- Provisional false-ignition rate: {p['false_ignition_rate']}

## Timeframe-local baselines

| TF | Rows | Start | End | Trades p50 | Trades p90 | Quote volume p50 | Quote volume p90 |
|---|---:|---|---|---:|---:|---:|---:|
{tfrows}

## Campaign-specific reconstruction

| Campaign | Start | End | Outcome | Reviewed states |
|---:|---|---|---|---|
{camps}

## Symbol-specific deductions

"""+'\n'.join(f'- {x}' for x in p['structural_notes'])+"""

## Unknowns and confidence limits

"""+'\n'.join(f'- {x}' for x in p['unknowns'])+"""

## Interpretation rule

Cross-coin comparison may compare mechanisms only after this symbol-specific profile and each campaign record have been read. A shared label does not imply a shared causal structure.
"""
    (d/'SYMBOL_STRUCTURAL_PROFILE.md').write_text(text,encoding='utf-8')
    campdir=d/'campaigns';campdir.mkdir(exist_ok=True)
    for c in p['campaigns']:
        ctext=f"""# {sym} Campaign {c['campaign_index']}

- Start: {c['start']}
- End: {c['end']}
- Outcome: {c['outcome']}
- Reviewed states: {', '.join(c['states']) or 'none'}
- Review counts: {json.dumps(c['review_counts'],sort_keys=True)}

## Dominant hypotheses
"""+'\n'.join(f'- {x}' for x in c['dominant_hypotheses'])+"""

## Competing hypotheses retained
"""+'\n'.join(f'- {x}' for x in c['alternative_hypotheses'])+"""

## Status

This campaign is independent evidence. It must not inherit the interpretation or terminal state of another campaign from the same symbol.
"""
        (campdir/f"CAMPAIGN_{c['campaign_index']:02d}.md").write_text(ctext,encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--case-root',type=Path,default=Path('research/case_studies'));ap.add_argument('--output-root',type=Path,default=Path('research/symbol_profiles'));ap.add_argument('--symbols',nargs='+',required=True);a=ap.parse_args()
    profiles=[]
    for s in a.symbols:
        p=profile(s,a.case_root);write_profile(p,a.output_root);profiles.append(p)
    rows='\n'.join(f"| {p['symbol']} | {len(p['campaigns'])} | {p['campaign_outcome_counts'].get('accepted_expansion',0)} | {p['campaign_outcome_counts'].get('failed_ignition',0)} | {p['source_conflicts']} | {', '.join(p['reliable_timeframes'])} |" for p in profiles)
    (a.output_root/'SYMBOL_PROFILE_INDEX.md').write_text('# Symbol Structural Profile Index\n\nProfiles are symbol-specific. Counts are descriptive and must not rank symbols.\n\n| Symbol | Campaigns | Accepted expansion | Failed ignition | Source conflicts | Reliable TFs |\n|---|---:|---:|---:|---:|---|\n'+rows+'\n',encoding='utf-8')
    print(json.dumps({'symbols':len(profiles),'campaigns':sum(len(p['campaigns']) for p in profiles)}))
if __name__=='__main__':main()
