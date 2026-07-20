# Black John Competing Hypothesis Engine

## Mission
Prevent pattern forcing by generating and testing multiple causal explanations for every campaign.

## Required hypothesis set
Create at least:
- one dominant hypothesis;
- one credible alternative;
- one failure/noise explanation;
- one `NEW_UNIDENTIFIED_STRUCTURE` hypothesis when the library does not explain the evidence cleanly.

Possible hypotheses include Quiet Accumulation, Bearish Build-up, Cold-Start OI Ignition, OI Reset Absorption, Short Covering Only, Price-led Vacuum Ignition, Whale Divergence, Failed Flash, Late Crowding, Distribution and continuation/reload paths. These names are candidate explanations, not conclusions.

## Hypothesis card
For each hypothesis record:
- prerequisites;
- expected ordered sequence;
- supporting evidence;
- opposing evidence;
- missing evidence;
- causal mechanism;
- historical successful analogues;
- historical failed analogues;
- discriminators;
- invalidation conditions;
- current research status.

## Adversarial review
Attempt to falsify the dominant hypothesis:
- What is the strongest alternative explanation?
- Is the evidence merely correlated with the outcome?
- Did the interpretation use future information?
- Does a failed case show the same surface signature?
- Is the claimed institutional intent identifiable from available data?
- Would the conclusion survive removal of one indicator?

## Selection rule
A dominant hypothesis must explain more of the ordered evidence with fewer unsupported assumptions than alternatives. Do not hide contradictory evidence. If no hypothesis dominates materially, return `UNRESOLVED` and state the next discriminating evidence.

## Output
Dominant hypothesis, alternatives, evidence matrix, uncertainty, discriminator, invalidation and abstention reason.