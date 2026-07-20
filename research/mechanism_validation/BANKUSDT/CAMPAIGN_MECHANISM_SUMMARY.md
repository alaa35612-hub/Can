# BANKUSDT Campaign Mechanism Metrics

Campaigns are measured independently against the symbol's own timeline. Missing stages remain missing; they are not inferred.

| Outcome | Campaigns | Median birth→ignition min | Median age at acceptance min | Median price reset depth % | Median OI reset depth % | Leading mechanisms |
|---|---:|---:|---:|---:|---:|---|
| accepted_expansion | 1 | 1590 | 1605 | -14.448713470718355 | -10.748591595275547 | {"EXECUTION_AND_PRICE_SIMULTANEOUS": 1} |
| failed_ignition | 3 | 135 | None | -0.9212287825370036 | -0.6504022463016457 | {"EXECUTION_AND_PRICE_SIMULTANEOUS": 3} |
| unresolved | 1 | None | None | -20.76196963799144 | -13.549369953317536 | {"EXECUTION_AND_PRICE_SIMULTANEOUS": 1} |

Reset depth is measured from the prior campaign's observed peak to the next campaign birth only when no observation gap interrupts the interval.
