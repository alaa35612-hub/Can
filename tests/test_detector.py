from __future__ import annotations

import unittest

from causal_upside.config import ScannerConfig
from causal_upside.detector import CausalUpsideDetector
from causal_upside.models import Hypothesis, Readiness, RuleStatus
from tests.helpers import make_bars


class DetectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = ScannerConfig(min_history=40, minimum_baseline_observations=24)
        self.detector = CausalUpsideDetector(self.config)

    def test_base_breakout_produces_explainable_candidate(self) -> None:
        result = self.detector.analyze(make_bars(100, breakout=True))
        self.assertIn(
            result.dominant_hypothesis,
            {
                Hypothesis.PRICE_LED_BASE_IGNITION,
                Hypothesis.POST_IGNITION_FUEL_RETENTION,
                Hypothesis.PRICE_LED_VACUUM_IGNITION,
            },
        )
        self.assertIn(result.readiness, {Readiness.LIVE_IGNITION, Readiness.ACCEPTED, Readiness.LATE_NO_CHASE, Readiness.CONTINUATION})
        self.assertTrue(result.supporting_evidence)
        self.assertTrue(result.next_discriminator)
        self.assertTrue(result.invalidation)

    def test_short_covering_is_not_promoted_as_bullish_discriminator(self) -> None:
        result = self.detector.analyze(make_bars(100, breakout=True, short_covering=True))
        self.assertNotEqual(result.dominant_hypothesis, Hypothesis.SHORT_COVERING_ONLY)
        self.assertIn(Hypothesis.SHORT_COVERING_ONLY, result.alternative_hypotheses + (result.failure_hypothesis,))

    def test_open_suffix_does_not_change_closed_cutoff(self) -> None:
        bars = make_bars(100, breakout=True)
        closed_result = self.detector.analyze(bars)
        open_bar = bars[-1]
        open_bar = type(open_bar)(**{**open_bar.to_dict(), "timestamp_ms": open_bar.timestamp_ms + self.config.interval_ms, "close_time_ms": open_bar.close_time_ms + self.config.interval_ms, "is_closed": False, "close": open_bar.close * 2, "high": open_bar.high * 2})
        with_open = self.detector.analyze(bars + [open_bar])
        self.assertEqual(closed_result.to_dict(), with_open.to_dict())

    def test_research_status_is_exposed(self) -> None:
        result = self.detector.analyze(make_bars(100, breakout=True))
        self.assertIn(result.research_status, set(RuleStatus))


if __name__ == "__main__":
    unittest.main()
