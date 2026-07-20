# Campaign Outcome Synthesis — Pass 1

## Scope and authority

This pass attaches forward 15m close paths only after each original frozen cutoff. It does not rewrite the State Ledger, convert hindsight into evidence, or impose one pattern across symbols.

The primary reading order is:

1. symbol structural profile;
2. campaign record;
3. reviewed transition status;
4. forward outcome audit;
5. matched-control comparison.

Medians are not authoritative when the number of campaign observations is small or the distribution is skewed. Observation count, forward-coverage status, source reliability, and control-relative path class must be read together.

## AKEUSDT

At the 720-minute comparison horizon:

- `IGNITION_CANDIDATE`: 4 observations; median terminal return about +1.51%.
- `ACCEPTED_IGNITION`: 3 observations; median terminal return about +3.42%.
- Accepted paths consist of one matched-control-like case, one negative-path outlier, and one case with incomplete forward coverage.
- `EXPANSION` has one completed positive-path outlier and one incomplete case.

Interpretation:

- Acceptance is not a stable discriminator for AKE in this corpus.
- AKE can produce a materially positive campaign, but the shared `ACCEPTED_IGNITION` label is insufficient by itself.
- Expansion is useful for describing an already developed campaign, not as an early predictive rule.

## BANKUSDT

At the 720-minute comparison horizon:

- `IGNITION_CANDIDATE`: 4 observations with mixed outcomes: one positive outlier, two negative outliers, and one control-like case.
- `ACCEPTED_IGNITION`: 1 observation; terminal return about +52.61%, classified as a positive-path outlier.
- `EXPANSION`: the same accepted campaign remained strongly positive.

Interpretation:

- BANK shows a provisional symbol-specific distinction between repeated ignition attempts and the single accepted campaign.
- This is not a general rule: the accepted sample size is one.
- BANK also has 412 preserved source conflicts, so source-selection sensitivity is mandatory before raising confidence.

## ESPORTSUSDT

At the 720-minute comparison horizon:

- `IGNITION_CANDIDATE`: 8 observations; median terminal return about +1.39%.
- `ACCEPTED_IGNITION`: 4 observations; median terminal return about +13.32%.
- Accepted paths consist of two matched-control-like cases, one negative-path outlier, and one incomplete case.
- No completed accepted case was classified as a positive-path outlier against its matched controls.

Interpretation:

- The high accepted-stage median is distribution-sensitive and must not be read as reliable discrimination.
- Large moves also occur in matched ESPORTS contexts.
- ESPORTS remains a recurrent-cycle symbol in which repeated build, ignition, failure, and rebuild episodes must stay separate.

## LYNUSDT

At the 720-minute comparison horizon:

- `CONFIRMED_BUILD`: 5 observations; median terminal return about +1.73%; three positive-path outliers and two control-like cases.
- `IGNITION_CANDIDATE`: 5 observations; median terminal return about +0.14%; four control-like cases and one positive outlier.
- `ACCEPTED_IGNITION`: 2 observations; one positive outlier and one control-like case.

Interpretation:

- For LYN, gradual confirmed build currently carries more discriminative information than the ignition shock itself.
- This is a symbol-specific research hypothesis, not a cross-coin rule.
- LYN has 214 preserved source conflicts, which caps confidence.

## Cross-symbol deductions

### Rejected as universal rules

1. `IGNITION_CANDIDATE` is sufficient for material continuation.
2. `ACCEPTED_IGNITION` has the same predictive meaning across symbols.
3. A higher median return alone proves stage quality.
4. `EXPANSION` should be treated as an early warning stage.

### Retained as research hypotheses

1. BANK may require a stricter acceptance gate than AKE, ESPORTS, or LYN.
2. LYN may be better characterized by persistent build quality than by ignition intensity.
3. ESPORTS may require cycle-frequency and reset-context features that are less important for the other symbols.
4. AKE may require campaign-age and gap-boundary context before acceptance can be interpreted.

### Methodological result

A shared state vocabulary is useful for indexing, but stage utility must be estimated within each symbol. The same label can be positive, ordinary, negative, or unresolved depending on the symbol and campaign.

## Control limitations

- Controls prefer causal `LATENT`, `FAILURE`, `RESET`, or `COOLING` cutoffs.
- Quiet cutoffs far from recent transitions are used only as a labeled fallback when inactive-state controls are insufficient.
- Metrics use close paths; intrabar high/low excursions are unavailable in the reconstructed timeline.
- Incomplete coverage is not extrapolated.

## Rule lifecycle decision

No result in this pass qualifies as a `DURABLE_RULE`.

- Universal ignition sufficiency: `REJECTED_RULE`.
- Universal acceptance sufficiency: `REJECTED_RULE`.
- BANK strict-acceptance mechanism: `RESEARCH_HYPOTHESIS`.
- LYN build-persistence mechanism: `RESEARCH_HYPOTHESIS`.
- ESPORTS recurrent-cycle mechanism: `RESEARCH_HYPOTHESIS`.
- AKE gap-aware campaign-age mechanism: `RESEARCH_HYPOTHESIS`.

## Required next validation

1. Audit rejected transition cutoffs as explicit negative controls without treating them as valid states.
2. Run source-selection sensitivity for BANK and LYN.
3. Measure campaign-age, reset depth, and build-to-ignition latency within each symbol.
4. Add further symbols before testing whether any mechanism transfers across assets.
