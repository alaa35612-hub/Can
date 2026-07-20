# AKEUSDT Campaign Mechanism Metrics

Campaigns are measured independently against the symbol's own timeline. Missing stages remain missing; they are not inferred.

| Outcome | Campaigns | Median birth→ignition min | Median age at acceptance min | Median price reset depth % | Median OI reset depth % | Leading mechanisms |
|---|---:|---:|---:|---:|---:|---|
| accepted_expansion | 2 | 247.5 | 262.5 | -56.40165713158414 | -6.594679964540551 | {"EXECUTION_AND_OI_SIMULTANEOUS": 1, "OI_LEADS": 1} |
| accepted_without_expansion | 1 | 2115 | 2130 | None | None | {"OI_LEADS": 1} |
| failed_ignition | 1 | 165 | None | None | None | {"OI_LEADS": 1} |

Reset depth is measured from the prior campaign's observed peak to the next campaign birth only when no observation gap interrupts the interval.
