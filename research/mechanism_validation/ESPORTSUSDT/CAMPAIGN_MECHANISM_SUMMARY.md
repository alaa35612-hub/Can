# ESPORTSUSDT Campaign Mechanism Metrics

Campaigns are measured independently against the symbol's own timeline. Missing stages remain missing; they are not inferred.

| Outcome | Campaigns | Median birth→ignition min | Median age at acceptance min | Median price reset depth % | Median OI reset depth % | Leading mechanisms |
|---|---:|---:|---:|---:|---:|---|
| accepted_expansion | 4 | 300.0 | 315.0 | -15.741762111546524 | -5.675470690747931 | {"EXECUTION_AND_PRICE_SIMULTANEOUS": 3, "OI_LEADS": 1} |
| failed_ignition | 4 | 202.5 | None | -0.7357859531772482 | -0.19770059161228204 | {"EXECUTION_AND_OI_SIMULTANEOUS": 1, "EXECUTION_AND_PRICE_SIMULTANEOUS": 1, "OI_LEADS": 2} |

Reset depth is measured from the prior campaign's observed peak to the next campaign birth only when no observation gap interrupts the interval.
