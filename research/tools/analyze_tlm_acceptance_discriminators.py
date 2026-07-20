from __future__ import annotations
import argparse,csv,json,math,statistics
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

M=60000; STEP=15*M; CHECKS=(0,15,30,45,60); VALID={'PASS','RESTRICT'}
METRICS=('price_return_pct','price_min_return_pct','oi_return_pct','positive_oi_fraction','execution_rank_median','execution_rank_last','execution_decay','taker_imbalance_median')

def n(v):
    try:
        x=float(v);return x if math.isfinite(x) else None
    except (TypeError,ValueError):return None

def med(xs):
    x=[v for v in xs if v is not None and math.isfinite(v)];return statistics.median(x) if x else None

def q(xs,p):
    x=sorted(v for v in xs if v is not None and math.isfinite(v))
    if not x:return None
    k=(len(x)-1)*p;a=int(k);b=min(a+1,len(x)-1);w=k-a
    return x[a]*(1-w)+x[b]*w

def pct(a,b):return None if a is None or b in (None,0) else (a/b-1)*100

def iso_ms(s):return int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)

def ms_iso(t):return datetime.fromtimestamp(t/1000,tz=timezone.utc).isoformat()

def load_json(p):return json.loads(p.read_text(encoding='utf-8'))

def load_csv(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def write_csv(p,rows):
    p.parent.mkdir(parents=True,exist_ok=True);fields=sorted({k for r in rows for k in r})
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def primary(raw):
    out=[]
    for r in raw:
        if r.get('timeframe')!='15m':continue
        t=int(float(r['timestamp']));x={'timestamp':t,'close_time':int(float(r.get('close_time') or t+STEP-1))}
        for k in ('close','oi','oi_change_pct','price_change_pct','number_of_trades_rank','quote_volume_rank','taker_quote_imbalance_pct'):
            x[k]=n(r.get(k))
        ranks=[v for v in (x['number_of_trades_rank'],x['quote_volume_rank']) if v is not None]
        x['execution_rank']=max(ranks) if ranks else None;out.append(x)
    return sorted(out,key=lambda r:r['timestamp'])

def status(x):return str(x.get('effective_status') or x.get('adversarial_status') or 'PASS')

def first(ts,state,valid=True):
    return next((x for x in ts if x.get('to_state')==state and (not valid or status(x) in VALID)),None)

def anchors(profile,ledger):
    out=[]
    for c in profile.get('campaigns',[]):
        a,b=iso_ms(c['start']),iso_ms(c['end']);ts=[x for x in ledger if a<=int(x['timestamp'])<=b]
        ign=first(ts,'IGNITION_CANDIDATE');any_ign=first(ts,'IGNITION_CANDIDATE',False)
        if not (ign or any_ign):continue
        z=ign or any_ign;acc=first(ts,'ACCEPTED_IGNITION');exp=first(ts,'EXPANSION');fail=first(ts,'FAILURE')
        rej=[x for x in ts if status(x).startswith('REJECT')]
        out.append({'campaign_index':int(c['campaign_index']),'outcome':c.get('outcome'),'ignition_timestamp':int(z['timestamp']),'ignition_time':z.get('time') or ms_iso(int(z['timestamp'])),'valid_ignition':ign is not None,'ignition_review_status':status(z),'acceptance_timestamp':int(acc['timestamp']) if acc else None,'expansion_timestamp':int(exp['timestamp']) if exp else None,'failure_timestamp':int(fail['timestamp']) if fail else None,'rejected_transition_count':len(rej),'rejected_states':sorted({x.get('to_state') for x in rej if x.get('to_state')}),'rejection_reasons':sorted({r for x in rej for r in (x.get('adversarial_reasons') or [])})})
    return sorted(out,key=lambda x:x['ignition_timestamp'])

def at(rows,t):
    i=None
    for j,r in enumerate(rows):
        if r['timestamp']<=t:i=j
        else:break
    return i

def metrics(rows,t,minutes):
    i=at(rows,t);j=at(rows,t+minutes*M)
    if i is None or rows[i]['timestamp']!=t:return {'coverage_status':'IGNITION_ROW_MISSING','checkpoint_minutes':minutes}
    if j is None or rows[j]['timestamp']<t+minutes*M:return {'coverage_status':'CHECKPOINT_NOT_CLOSED','checkpoint_minutes':minutes}
    w=rows[i:j+1]
    if any(y['timestamp']-x['timestamp']>STEP for x,y in zip(w,w[1:])):return {'coverage_status':'OBSERVATION_GAP','checkpoint_minutes':minutes}
    a,z=w[0],w[-1];pr=[pct(x['close'],a['close']) for x in w];post=w[1:]
    return {'coverage_status':'COMPLETE','checkpoint_minutes':minutes,'checkpoint_timestamp':z['timestamp'],'checkpoint_time':ms_iso(z['timestamp']),'rows_visible':len(w),'price_return_pct':pct(z['close'],a['close']),'price_min_return_pct':min((x for x in pr if x is not None),default=None),'oi_return_pct':pct(z['oi'],a['oi']),'positive_oi_fraction':(sum((x['oi_change_pct'] or 0)>0 for x in post if x['oi_change_pct'] is not None)/sum(x['oi_change_pct'] is not None for x in post)) if any(x['oi_change_pct'] is not None for x in post) else None,'execution_rank_median':med([x['execution_rank'] for x in w]),'execution_rank_last':z['execution_rank'],'execution_decay':None if z['execution_rank'] is None or a['execution_rank'] is None else z['execution_rank']-a['execution_rank'],'taker_imbalance_median':med([x['taker_quote_imbalance_pct'] for x in w])}

def baseline(history,t,minutes):
    p=[r for r in history if r['ignition_timestamp']<t and r['checkpoint_minutes']==minutes and r['coverage_status']=='COMPLETE']
    return {'prior_campaign_indices':[r['campaign_index'] for r in p],'prior_campaign_count':len(p),'medians':{k:med([r.get(k) for r in p]) for k in METRICS},'counts':{k:sum(r.get(k) is not None for r in p) for k in METRICS}}

def cmp(a,b):return 'MISSING' if a is None or b is None else ('ABOVE' if a>b else 'BELOW' if a<b else 'AT')

def assess(x,b):
    if x['coverage_status']!='COMPLETE':return {'assessment_status':'ABSTAIN_'+x['coverage_status'],'dominant_hypothesis':'UNRESOLVED','supporting_evidence':[],'opposing_evidence':[],'missing_evidence':['complete checkpoint coverage']}
    if x['checkpoint_minutes']==0:return {'assessment_status':'IGNITION_SNAPSHOT_ONLY','dominant_hypothesis':'UNRESOLVED','supporting_evidence':['ignition proposal frozen'],'opposing_evidence':[],'missing_evidence':['post-ignition sequence']}
    req=('price_return_pct','oi_return_pct','execution_rank_median')
    if any(b['counts'][k]<2 or x.get(k) is None or b['medians'][k] is None for k in req):return {'assessment_status':'ABSTAIN_INSUFFICIENT_PRIOR_BASELINE','dominant_hypothesis':'UNRESOLVED','supporting_evidence':[],'opposing_evidence':[],'missing_evidence':[k for k in req if b['counts'][k]<2 or x.get(k) is None or b['medians'][k] is None]}
    ev={k:cmp(x.get(k),b['medians'].get(k)) for k in METRICS};price=x['price_return_pct'];oi=x['oi_return_pct'];dec=x['execution_decay']
    if all(ev[k] in {'ABOVE','AT'} for k in req):h,s='TLM_POST_IGNITION_FUEL_RETENTION','FULL_FUEL_RETENTION_CONTEXT'
    elif price>0 and oi<0 and dec is not None and dec<0:h,s='TLM_SHORT_COVERING_ONLY','SHORT_COVERING_CONTEXT'
    elif ev['price_return_pct']=='BELOW' and ev['oi_return_pct']=='BELOW' and dec is not None and dec<0:h,s='TLM_TRANSIENT_EXECUTION_SPIKE','TRANSIENT_FAILURE_CONTEXT'
    else:h,s='NEW_UNIDENTIFIED_STRUCTURE','MIXED_CONTEXT'
    return {'assessment_status':s,'dominant_hypothesis':h,'supporting_evidence':[f'{k}={v}' for k,v in ev.items() if v=='ABOVE'],'opposing_evidence':[f'{k}={v}' for k,v in ev.items() if v=='BELOW'],'missing_evidence':[k for k in METRICS if x.get(k) is None],'evidence_vs_prior_median':ev}

def freeze(rows,aa):
    frozen=[];trace=[];history=[]
    for a in aa:
        current=[]
        for m in CHECKS:
            x=metrics(rows,a['ignition_timestamp'],m);b=baseline(history,a['ignition_timestamp'],m);d=assess(x,b)
            r={'record_type':'FROZEN_CHECKPOINT_ASSESSMENT','symbol':'TLMUSDT','campaign_index':a['campaign_index'],'outcome_hidden':True,'valid_ignition':a['valid_ignition'],'ignition_review_status':a['ignition_review_status'],'ignition_timestamp':a['ignition_timestamp'],'ignition_time':a['ignition_time'],'checkpoint_minutes':m,'metrics':x,'causal_baselines':b,**d};frozen.append(r);trace.append(r);current.append({'campaign_index':a['campaign_index'],'ignition_timestamp':a['ignition_timestamp'],'checkpoint_minutes':m,**x})
        history+=current;trace.append({'record_type':'OUTCOME_REVEALED_AFTER_ALL_CHECKPOINTS','symbol':'TLMUSDT','campaign_index':a['campaign_index'],'outcome_hidden':False,'outcome':a['outcome'],'acceptance_timestamp':a['acceptance_timestamp'],'expansion_timestamp':a['expansion_timestamp'],'failure_timestamp':a['failure_timestamp'],'rejected_transition_count':a['rejected_transition_count'],'rejected_states':a['rejected_states'],'rejection_reasons':a['rejection_reasons'],'historical_assessment_rewritten':False})
    return frozen,trace

def group(o):return 'SUCCESS' if o=='accepted_expansion' else 'PARTIAL' if o=='accepted_without_expansion' else 'FAILURE' if o=='failed_ignition' else 'UNRESOLVED'

def cliff(a,b):
    if not a or not b:return None
    return (sum(x>y for x in a for y in b)-sum(x<y for x in a for y in b))/(len(a)*len(b))

def matrix(frozen,aa):
    outcomes={a['campaign_index']:group(a['outcome']) for a in aa};out=[]
    for m in CHECKS[1:]:
        rr=[r for r in frozen if r['checkpoint_minutes']==m and r['valid_ignition'] and r['metrics']['coverage_status']=='COMPLETE']
        for k in METRICS:
            s=[r['metrics'][k] for r in rr if outcomes[r['campaign_index']]=='SUCCESS' and r['metrics'].get(k) is not None];f=[r['metrics'][k] for r in rr if outcomes[r['campaign_index']]=='FAILURE' and r['metrics'].get(k) is not None]
            if len(s)<2 or len(f)<2:state='INSUFFICIENT_PAIRED_SAMPLE'
            elif min(s)>max(f):state='NON_OVERLAPPING_SUCCESS_ABOVE_FAILURE'
            elif min(f)>max(s):state='NON_OVERLAPPING_FAILURE_ABOVE_SUCCESS'
            else:state='OVERLAPPING_OBSERVED_RANGES'
            out.append({'checkpoint_minutes':m,'metric':k,'success_count':len(s),'failure_count':len(f),'success_median':med(s),'failure_median':med(f),'success_q25':q(s,.25),'success_q75':q(s,.75),'failure_q25':q(f,.25),'failure_q75':q(f,.75),'cliff_delta':cliff(s,f),'observed_range_status':state})
    return out

def flatten(r):
    x=r['metrics'];b=r['causal_baselines'];z={'campaign_index':r['campaign_index'],'valid_ignition':r['valid_ignition'],'ignition_time':r['ignition_time'],'checkpoint_minutes':r['checkpoint_minutes'],'coverage_status':x['coverage_status'],'assessment_status':r['assessment_status'],'dominant_hypothesis':r['dominant_hypothesis'],'prior_campaign_count':b['prior_campaign_count'],'prior_campaign_indices':'|'.join(map(str,b['prior_campaign_indices'])),'supporting_evidence':'|'.join(r['supporting_evidence']),'opposing_evidence':'|'.join(r['opposing_evidence']),'missing_evidence':'|'.join(r['missing_evidence'])}
    for k in METRICS:z[k]=x.get(k);z[k+'_prior_median']=b['medians'].get(k)
    return z

def sequence(aa):
    out=[]
    for a in aa:
        out.append({'campaign_index':a['campaign_index'],'outcome_group':group(a['outcome']),'outcome':a['outcome'],'valid_ignition':a['valid_ignition'],'ignition_review_status':a['ignition_review_status'],'ignition_time':a['ignition_time'],'ignition_to_acceptance_minutes':None if a['acceptance_timestamp'] is None else int((a['acceptance_timestamp']-a['ignition_timestamp'])/M),'acceptance_to_expansion_minutes':None if a['acceptance_timestamp'] is None or a['expansion_timestamp'] is None else int((a['expansion_timestamp']-a['acceptance_timestamp'])/M),'ignition_to_failure_minutes':None if a['failure_timestamp'] is None else int((a['failure_timestamp']-a['ignition_timestamp'])/M),'rejected_transition_count':a['rejected_transition_count'],'rejected_states':'|'.join(a['rejected_states']),'rejection_reasons':'|'.join(a['rejection_reasons'])})
    return out

def cards(frozen,aa):
    outcomes={a['campaign_index']:group(a['outcome']) for a in aa};defs={'TLM_POST_IGNITION_FUEL_RETENTION':'price, OI and execution persist after ignition','TLM_SHORT_COVERING_ONLY':'price rises while OI contracts and execution decays','TLM_TRANSIENT_EXECUTION_SPIKE':'execution spike loses price and OI support','NEW_UNIDENTIFIED_STRUCTURE':'mixed ordered evidence'};out=[]
    for h,mechanism in defs.items():
        rr=[r for r in frozen if r['dominant_hypothesis']==h and r['checkpoint_minutes'] in {30,45,60}]
        out.append({'hypothesis_id':h,'causal_mechanism':mechanism,'supporting_campaigns':sorted({r['campaign_index'] for r in rr if outcomes[r['campaign_index']]=='SUCCESS'}),'failed_analogues':sorted({r['campaign_index'] for r in rr if outcomes[r['campaign_index']]=='FAILURE'}),'partial_analogues':sorted({r['campaign_index'] for r in rr if outcomes[r['campaign_index']]=='PARTIAL'}),'current_status':'RESEARCH_HYPOTHESIS','invalidation':'must fail if opposing ordered evidence dominates at a later frozen cutoff'})
    return out

def render(summary):
    rr='\n'.join(f"| {r['checkpoint_minutes']} | {r['metric']} | {r['success_count']} | {r['failure_count']} | {r['success_median']} | {r['failure_median']} | {r['cliff_delta']} | {r['observed_range_status']} |" for r in summary['non_overlapping_metrics']) or '| — | — | 0 | 0 | — | — | — | none |'
    c=summary['outcome_counts']
    return f"""# TLMUSDT Acceptance-Discriminator Blind Replay — Raw Pass

- Ignition-anchor campaigns: {summary['campaigns']}
- Valid ignition campaigns: {summary['valid_ignitions']}
- Accepted expansion: {c.get('SUCCESS',0)}
- Accepted without expansion: {c.get('PARTIAL',0)}
- Failed ignition: {c.get('FAILURE',0)}
- Frozen checkpoints: {', '.join(map(str,CHECKS))} minutes

## Descriptive non-overlapping observed ranges

| Checkpoint | Metric | Success n | Failure n | Success median | Failure median | Cliff delta | Status |
|---:|---|---:|---:|---:|---:|---:|---|
{rr}

These ranges are descriptive, not production thresholds. The human-reviewed layer must test failed analogues, repeated-campaign dependence and matched controls before any lifecycle change.
"""

def main():
    p=argparse.ArgumentParser();p.add_argument('--case-root',type=Path,default=Path('research/oos_validation/esports_subtype/case_studies'));p.add_argument('--profile-root',type=Path,default=Path('research/oos_validation/esports_subtype/symbol_profiles'));p.add_argument('--output-root',type=Path,default=Path('research/tlm_acceptance_discriminators'));a=p.parse_args();g=a.case_root/'TLMUSDT'/'generated'
    rows=primary(load_csv(g/'TLM_CAUSAL_TIMELINE.csv'));ledger=load_json(g/'TLM_REVIEWED_STATE_LEDGER.json');profile=load_json(a.profile_root/'TLMUSDT'/'SYMBOL_STRUCTURAL_PROFILE.json');aa=anchors(profile,ledger);frozen,trace=freeze(rows,aa);mx=matrix(frozen,aa);cc=cards(frozen,aa);seq=sequence(aa);counts=Counter(group(x['outcome']) for x in aa);summary={'symbol':'TLMUSDT','campaigns':len(aa),'valid_ignitions':sum(x['valid_ignition'] for x in aa),'outcome_counts':dict(counts),'non_overlapping_metrics':[x for x in mx if x['observed_range_status'].startswith('NON_OVERLAPPING')],'hypothesis_cards':cc,'constraints':['outcome revealed after all checkpoints','prior TLM campaigns only','campaign is independent unit','no lifecycle promotion in raw pass']}
    a.output_root.mkdir(parents=True,exist_ok=True);write_csv(a.output_root/'TLM_FROZEN_CHECKPOINT_ASSESSMENTS.csv',[flatten(x) for x in frozen]);write_csv(a.output_root/'TLM_SEQUENCE_AND_REJECTION_SUMMARY.csv',seq);write_csv(a.output_root/'TLM_DISCRIMINATOR_MATRIX.csv',mx);(a.output_root/'TLM_HYPOTHESIS_CARDS.json').write_text(json.dumps(cc,indent=2),encoding='utf-8');(a.output_root/'TLM_RAW_REPLAY_SUMMARY.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');(a.output_root/'TLM_RAW_REPLAY_SUMMARY.md').write_text(render(summary),encoding='utf-8')
    with (a.output_root/'TLM_FROZEN_REPLAY_TRACE.jsonl').open('w',encoding='utf-8') as f:
        for x in trace:f.write(json.dumps(x,sort_keys=True)+'\n')
    print(json.dumps({'campaigns':len(aa),'frozen_assessments':len(frozen),'trace_records':len(trace),'discriminator_rows':len(mx)}))

if __name__=='__main__':main()
