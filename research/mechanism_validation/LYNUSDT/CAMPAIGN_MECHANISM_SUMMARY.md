# LYNUSDT Campaign Mechanism Metrics

Campaigns are measured independently against the symbol's own timeline. Missing stages remain missing; they are not inferred.

| Outcome | Campaigns | Median birth→ignition min | Median age at acceptance min | Median price reset depth % | Median OI reset depth % | Leading mechanisms |
|---|---:|---:|---:|---:|---:|---|
| accepted_expansion | 2 | 1012.5 | 1027.5 | -1.7336268574573488 | -0.9179488947207437 | {"EXECUTION_AND_OI_SIMULTANEOUS": 1, "EXECUTION_AND_PRICE_SIMULTANEOUS": 1} |
| failed_ignition | 3 | 1050 | None | -2.3948760790866053 | -1.6259880079444011 | {"EXECUTION_AND_OI_SIMULTANEOUS": 3} |

Reset depth is measured from the prior campaign's observed peak to the next campaign birth only when no observation gap interrupts the interval.
