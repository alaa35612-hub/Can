from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from causal_upside.config import ScannerConfig
from causal_upside.detector import CausalUpsideDetector
from causal_upside.ledger import LedgerStore
from causal_upside.models import CampaignState, EvidenceItem, Hypothesis, Readiness
from tests.helpers import make_bars


class LedgerTests(unittest.TestCase):
    def test_restart_continuity_and_failure_hysteresis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = ScannerConfig(min_history=40, minimum_baseline_observations=24, state_dir=Path(directory))
            detector = CausalUpsideDetector(config)
            store = LedgerStore(config)
            accepted = detector.analyze(make_bars(100, breakout=True))
            accepted = replace(accepted, campaign_state=CampaignState.ACCEPTED_IGNITION, readiness=Readiness.ACCEPTED)
            first = store.update(accepted)
            self.assertEqual(store.load(first.symbol, first.timeframe).last_observed_ms, accepted.cutoff_ms)

            failure_evidence = (
                EvidenceItem("acceptance", "base acceptance failed", accepted.cutoff_ms + config.interval_ms, "STRONG"),
                EvidenceItem("execution", "execution decayed", accepted.cutoff_ms + config.interval_ms, "STRONG"),
            )
            failure_one = replace(
                accepted,
                cutoff_ms=accepted.cutoff_ms + config.interval_ms,
                campaign_state=CampaignState.FAILURE,
                readiness=Readiness.FAILED,
                dominant_hypothesis=Hypothesis.FAILED_FLASH,
                supporting_evidence=failure_evidence,
            )
            cooling = store.update(failure_one)
            self.assertEqual(cooling.state, CampaignState.COOLING)
            failure_two = replace(failure_one, cutoff_ms=failure_one.cutoff_ms + config.interval_ms)
            failed = LedgerStore(config).update(failure_two)
            self.assertEqual(failed.state, CampaignState.FAILURE)

    def test_out_of_order_update_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = ScannerConfig(min_history=40, minimum_baseline_observations=24, state_dir=Path(directory))
            result = CausalUpsideDetector(config).analyze(make_bars(100, breakout=True))
            store = LedgerStore(config)
            current = store.update(result)
            stale = replace(result, cutoff_ms=result.cutoff_ms - config.interval_ms)
            self.assertEqual(store.update(stale).last_observed_ms, current.last_observed_ms)


if __name__ == "__main__":
    unittest.main()
