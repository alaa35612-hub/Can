"""Atomic persistent campaign ledger with deterministic hysteresis."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .config import ScannerConfig
from .models import CampaignLedger, CampaignState, Hypothesis, Readiness, SignalAssessment


PROGRESSIVE = {
    CampaignState.LATENT: 0,
    CampaignState.EARLY_BUILD: 1,
    CampaignState.CONFIRMED_BUILD: 2,
    CampaignState.REBUILD: 2,
    CampaignState.ARMED: 3,
    CampaignState.IGNITION_CANDIDATE: 4,
    CampaignState.ACCEPTED_IGNITION: 5,
    CampaignState.EXPANSION: 6,
    CampaignState.CONTINUATION_RELOAD: 7,
    CampaignState.COOLING: 7,
    CampaignState.RESET: 1,
    CampaignState.FAILURE: -1,
    CampaignState.DISTRIBUTION: -1,
    CampaignState.UNRESOLVED: 0,
}


class LedgerStore:
    def __init__(self, config: ScannerConfig):
        self.config = config.validate()
        self.root = self.config.state_dir
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, symbol: str, timeframe: str) -> Path:
        safe = "".join(char for char in f"{symbol}_{timeframe}" if char.isalnum() or char in "-_")
        return self.root / f"{safe}.json"

    def load(self, symbol: str, timeframe: str) -> CampaignLedger | None:
        path = self.path(symbol, timeframe)
        if not path.exists():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        if int(value.get("schema_version", -1)) != self.config.ledger_schema_version:
            raise ValueError(f"Unsupported ledger schema in {path}")
        value["state"] = CampaignState(value["state"])
        value["dominant_hypothesis"] = Hypothesis(value["dominant_hypothesis"])
        value["alternatives"] = [Hypothesis(item) for item in value.get("alternatives", [])]
        return CampaignLedger(**value)

    def save(self, ledger: CampaignLedger) -> None:
        path = self.path(ledger.symbol, ledger.timeframe)
        payload = json.dumps(ledger.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        descriptor, temporary = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def update(self, assessment: SignalAssessment) -> CampaignLedger:
        prior = self.load(assessment.symbol, assessment.timeframe)
        if prior and assessment.cutoff_ms <= prior.last_observed_ms:
            return prior
        if prior is None:
            ledger = CampaignLedger(
                schema_version=self.config.ledger_schema_version,
                symbol=assessment.symbol,
                timeframe=assessment.timeframe,
                campaign_id=f"{assessment.symbol}-{assessment.timeframe}-{assessment.cutoff_ms}",
                state=CampaignState.LATENT,
                birth_ms=assessment.cutoff_ms,
                last_observed_ms=assessment.cutoff_ms,
            )
        else:
            ledger = prior

        proposed = assessment.campaign_state
        negative = proposed in {CampaignState.FAILURE, CampaignState.DISTRIBUTION}
        independent_negative_categories = {item.category for item in assessment.opposing_evidence}
        strong_failure_categories = {item.category for item in assessment.supporting_evidence if item.strength == "STRONG"} if negative else set()
        if negative and len(strong_failure_categories | independent_negative_categories) >= 2:
            ledger.contradiction_streak += 1
        elif negative:
            ledger.contradiction_streak = max(ledger.contradiction_streak, 1)
        else:
            ledger.contradiction_streak = 0

        previous_state = ledger.state
        if negative and ledger.state not in {CampaignState.LATENT, CampaignState.UNRESOLVED} and ledger.contradiction_streak < 2:
            next_state = CampaignState.COOLING
        elif proposed == CampaignState.UNRESOLVED and PROGRESSIVE.get(ledger.state, 0) > 0:
            next_state = ledger.state
        elif PROGRESSIVE.get(proposed, 0) >= PROGRESSIVE.get(ledger.state, 0) or negative:
            next_state = proposed
        else:
            next_state = CampaignState.COOLING

        ledger.state = next_state
        ledger.last_observed_ms = assessment.cutoff_ms
        ledger.dominant_hypothesis = assessment.dominant_hypothesis
        ledger.alternatives = list(assessment.alternative_hypotheses)
        ledger.last_assessment = assessment.to_dict()
        if ledger.first_detection_ms is None and next_state not in {CampaignState.LATENT, CampaignState.UNRESOLVED}:
            ledger.first_detection_ms = assessment.cutoff_ms
        if ledger.first_warning_ms is None and assessment.readiness in {Readiness.CONFIRMED_BUILD, Readiness.ARMED, Readiness.LIVE_IGNITION, Readiness.ACCEPTED}:
            ledger.first_warning_ms = assessment.cutoff_ms
        timestamp_fields = {
            CampaignState.ARMED: "armed_ms",
            CampaignState.IGNITION_CANDIDATE: "ignition_ms",
            CampaignState.ACCEPTED_IGNITION: "acceptance_ms",
            CampaignState.EXPANSION: "expansion_ms",
            CampaignState.COOLING: "weakness_ms",
            CampaignState.FAILURE: "failure_ms",
            CampaignState.RESET: "reset_ms",
            CampaignState.REBUILD: "rebuild_ms",
        }
        field = timestamp_fields.get(next_state)
        if field and getattr(ledger, field) is None:
            setattr(ledger, field, assessment.cutoff_ms)
        if previous_state != next_state:
            ledger.transition_history.append(
                {
                    "timestamp_ms": assessment.cutoff_ms,
                    "from_state": previous_state.value,
                    "to_state": next_state.value,
                    "dominant_hypothesis": assessment.dominant_hypothesis.value,
                    "supporting_categories": sorted({item.category for item in assessment.supporting_evidence}),
                    "opposing_categories": sorted({item.category for item in assessment.opposing_evidence}),
                    "quality_flags": list(assessment.quality_flags),
                }
            )
        self.save(ledger)
        return ledger
