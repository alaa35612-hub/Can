from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

FULL_CONTEXT = "FULL_TRANSFER_CONTEXT"
SUCCESS = "SUCCESS"
FAILURE = "FAILURE"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def truthy(value: Any) -> bool:
    return str(value).lower() == "true"


def number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_records(output_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted((output_root / "transfer_assessments").glob("*/FROZEN_CAMPAIGN_TRANSFER_ASSESSMENTS.csv")):
        for raw in load_csv(path):
            records.append(
                {
                    **raw,
                    "campaign_index": int(float(raw.get("campaign_index") or 0)),
                    "terminal_return_pct": number(raw.get("terminal_return_pct")),
                    "forward_coverage_complete": truthy(raw.get("forward_coverage_complete")),
                }
            )
    return records


def reviewed_findings(records: list[dict[str, Any]]) -> dict[str, Any]:
    evaluable = [item for item in records if not str(item.get("assessment_status", "")).startswith("ABSTAIN")]
    abstained = [item for item in records if str(item.get("assessment_status", "")).startswith("ABSTAIN")]
    full = [item for item in evaluable if item.get("assessment_status") == FULL_CONTEXT]
    full_successes = [item for item in full if item.get("outcome_group") == SUCCESS]
    full_failures = [item for item in full if item.get("outcome_group") == FAILURE]
    nonfull_successes = [
        item for item in evaluable
        if item.get("assessment_status") != FULL_CONTEXT and item.get("outcome_group") == SUCCESS
    ]
    effective_symbols = sorted({str(item.get("symbol")) for item in evaluable})
    abstained_symbols = sorted({str(item.get("symbol")) for item in abstained} - set(effective_symbols))

    sufficiency_decision = "REJECT" if full_failures else "NOT_REJECTED_IN_THIS_SAMPLE"
    necessity_decision = "REJECT" if nonfull_successes else "NOT_REJECTED_IN_THIS_SAMPLE"
    if len(effective_symbols) < 2:
        association_result = "INSUFFICIENT_INDEPENDENT_SYMBOL_SAMPLE"
    elif full_failures and full_successes:
        association_result = "MIXED_EXTERNAL_ASSOCIATION"
    elif full_failures:
        association_result = "NEGATIVE_EXTERNAL_DIRECTION"
    elif len(full_successes) >= 2:
        association_result = "DIRECTIONAL_EXTERNAL_ASSOCIATION"
    else:
        association_result = "INSUFFICIENT_EXTERNAL_CONTEXT_SAMPLE"

    return {
        "comparison_unit": "CAMPAIGN",
        "records_total": len(records),
        "evaluable_campaigns": len(evaluable),
        "abstained_campaigns": len(abstained),
        "effective_symbols": effective_symbols,
        "abstained_only_symbols": abstained_symbols,
        "full_context_success_campaigns": [
            {"symbol": item["symbol"], "campaign_index": item["campaign_index"]}
            for item in full_successes
        ],
        "full_context_failure_campaigns": [
            {
                "symbol": item["symbol"],
                "campaign_index": item["campaign_index"],
                "path_class": item.get("path_class"),
                "terminal_return_pct": item.get("terminal_return_pct"),
                "rejected_transition_count": int(float(item.get("rejected_transition_count") or 0)),
            }
            for item in full_failures
        ],
        "nonfull_success_campaigns": [
            {
                "symbol": item["symbol"],
                "campaign_index": item["campaign_index"],
                "assessment_status": item.get("assessment_status"),
                "path_class": item.get("path_class"),
            }
            for item in nonfull_successes
        ],
        "sufficiency_claim": {
            "rule_id": "MATURE_DEEP_RESET_CONTEXT_CROSS_SYMBOL_SUFFICIENCY",
            "current_status": "RESEARCH_HYPOTHESIS",
            "decision": sufficiency_decision,
            "basis": (
                "At least one evaluable external campaign satisfied the full context and still failed structural acceptance."
                if full_failures
                else "No full-context structural failure was observed in the evaluable external sample."
            ),
        },
        "necessity_claim": {
            "rule_id": "MATURE_DEEP_RESET_CONTEXT_CROSS_SYMBOL_NECESSITY",
            "current_status": "RESEARCH_HYPOTHESIS",
            "decision": necessity_decision,
            "basis": (
                "At least one evaluable external campaign achieved accepted expansion without the full context."
                if nonfull_successes
                else "No evaluable accepted expansion without full context was observed."
            ),
        },
        "association_result": association_result,
        "source_rule": {
            "rule_id": "ESPORTS_MATURE_DEEP_RESET_SUBTYPE",
            "current_status": "RESEARCH_HYPOTHESIS",
            "decision": "KEEP_AS_ESPORTS_SPECIFIC_HYPOTHESIS",
            "basis": "External transfer evidence does not rewrite the original frozen ESPORTS campaigns.",
        },
        "status_counts": dict(Counter(str(item.get("assessment_status")) for item in records)),
        "promotion_prohibited": True,
    }


def render_findings(findings: dict[str, Any]) -> str:
    full_failures = findings["full_context_failure_campaigns"]
    nonfull_successes = findings["nonfull_success_campaigns"]
    failure_lines = "\n".join(
        f"- {item['symbol']} campaign {item['campaign_index']}: structural failure; "
        f"path class `{item['path_class']}`; terminal return {item['terminal_return_pct']}%; "
        f"rejected transitions {item['rejected_transition_count']}."
        for item in full_failures
    ) or "- None."
    success_lines = "\n".join(
        f"- {item['symbol']} campaign {item['campaign_index']}: accepted expansion under "
        f"`{item['assessment_status']}`; path class `{item['path_class']}`."
        for item in nonfull_successes
    ) or "- None."
    return f"""# Human-Reviewed ESPORTS Subtype OOS Findings

The raw frozen assessments remain unchanged. This review separates abstention, structural outcome and forward return, and evaluates claims at the campaign unit.

## Effective sample

- Total ignition assessments: {findings['records_total']}
- Evaluable campaigns: {findings['evaluable_campaigns']}
- Abstained campaigns: {findings['abstained_campaigns']}
- Symbols with evaluable campaigns: {', '.join(findings['effective_symbols']) or 'none'}
- Symbols contributing abstention only: {', '.join(findings['abstained_only_symbols']) or 'none'}
- Association result: `{findings['association_result']}`

MAGMA and VELVET abstentions are missing-history evidence, not failed subtype cases.

## Full-context counterexamples

{failure_lines}

A structural failure can still have a positive nominal return. The matched-control path class is therefore retained separately from the campaign-state outcome.

## Successful campaigns without full context

{success_lines}

These campaigns reject cross-symbol necessity; they do not prove that partial context is sufficient.

## Rule lifecycle

- `MATURE_DEEP_RESET_CONTEXT_CROSS_SYMBOL_SUFFICIENCY`: `{findings['sufficiency_claim']['decision']}`.
- `MATURE_DEEP_RESET_CONTEXT_CROSS_SYMBOL_NECESSITY`: `{findings['necessity_claim']['decision']}`.
- `ESPORTS_MATURE_DEEP_RESET_SUBTYPE`: `KEEP_AS_ESPORTS_SPECIFIC_HYPOTHESIS`.
- Cross-symbol association remains `{findings['association_result']}` because only one external symbol supplied evaluable campaigns.
- No rule is promoted to `SUPPORTED_PATTERN`, `CONDITIONAL_RULE`, or `DURABLE_RULE`.

## Interpretation boundary

The TLM counterexample rejects the claim that the frozen conjunction is sufficient for accepted expansion across symbols. It does not prove that deep-reset maturity is irrelevant, and it does not invalidate the ESPORTS-specific subtype. Estimating external association requires additional independent symbols with enough prior campaigns to avoid abstention.
"""


def render_lifecycle(findings: dict[str, Any]) -> str:
    rows = [findings["source_rule"], findings["sufficiency_claim"], findings["necessity_claim"]]
    table = "\n".join(
        f"| {item['rule_id']} | {item['current_status']} | {item['decision']} | {item['basis']} |"
        for item in rows
    )
    return f"""# Reviewed OOS Rule Lifecycle Decisions

| Rule | Current status | Decision | Evidence basis |
|---|---|---|---|
{table}

- External association result: `{findings['association_result']}`.
- No promotion beyond `RESEARCH_HYPOTHESIS` is allowed by this pass.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    findings = reviewed_findings(load_records(args.output_root))
    (args.output_root / "HUMAN_REVIEWED_OOS_FINDINGS.json").write_text(
        json.dumps(findings, indent=2), encoding="utf-8"
    )
    (args.output_root / "HUMAN_REVIEWED_OOS_FINDINGS.md").write_text(
        render_findings(findings), encoding="utf-8"
    )
    decisions = [findings["source_rule"], findings["sufficiency_claim"], findings["necessity_claim"]]
    (args.output_root / "REVIEWED_RULE_LIFECYCLE_DECISIONS.json").write_text(
        json.dumps(decisions, indent=2), encoding="utf-8"
    )
    (args.output_root / "REVIEWED_RULE_LIFECYCLE_DECISIONS.md").write_text(
        render_lifecycle(findings), encoding="utf-8"
    )
    print(json.dumps(findings))


if __name__ == "__main__":
    main()
