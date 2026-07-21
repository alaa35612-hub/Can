from __future__ import annotations

import unittest

from causal_upside.models import (
    CampaignState,
    Confidence,
    EvidenceItem,
    Hypothesis,
    Readiness,
    Reliability,
    RuleStatus,
    SignalAssessment,
)
from run_causal_upside_scanner import SETTINGS, build_config, render_console_report


class EditorRunnerTests(unittest.TestCase):
    def test_editor_settings_build_validated_config(self) -> None:
        settings = dict(SETTINGS)
        settings.update(
            {
                "TIMEFRAME": "5m",
                "CANDLES": 120,
                "MIN_HISTORY": 60,
                "SCAN_ALL_USDT_PERPETUALS": False,
                "SYMBOL_WHITELIST": ["akeusdt", "TLMUSDT", "AKEUSDT"],
            }
        )
        config = build_config(settings)
        self.assertEqual(config.timeframe, "5m")
        self.assertEqual(config.history_limit, 120)
        self.assertEqual(config.whitelist, ("AKEUSDT", "TLMUSDT"))
        self.assertFalse(config.scan_all_usdt_perpetuals)

    def test_report_exposes_research_reasoning(self) -> None:
        config = build_config({**SETTINGS, "RUN_CONTINUOUSLY": False})
        assessment = SignalAssessment(
            symbol="AKEUSDT",
            timeframe="15m",
            cutoff_ms=1_784_016_899_999,
            campaign_state=CampaignState.ARMED,
            dominant_hypothesis=Hypothesis.QUIET_ACCUMULATION,
            alternative_hypotheses=(Hypothesis.PRICE_LED_BASE_IGNITION,),
            failure_hypothesis=Hypothesis.TRANSIENT_EXECUTION_SPIKE,
            structural_bias="EARLY_BULLISH_STRUCTURE",
            signal_importance="HIGH_STRUCTURAL_IMPORTANCE",
            readiness=Readiness.ARMED,
            entry_safety="CONDITIONAL_WAIT_FOR_ACCEPTANCE",
            confidence=Confidence.MEDIUM_HIGH,
            data_reliability=Reliability.HIGH,
            supporting_evidence=(
                EvidenceItem("price", "price retained above the local base", 1_784_016_899_999, "STRONG"),
            ),
            opposing_evidence=(),
            missing_evidence=("post-trigger acceptance",),
            next_discriminator="closed breakout with retained execution",
            invalidation="close below the reconstructed base",
            abstention_reason=None,
            research_status=RuleStatus.RESEARCH_HYPOTHESIS,
            campaign_age_bars=12,
            distance_from_footprint_rank=0.22,
            quality_flags=(),
        )
        report = render_console_report([assessment], config, cycle=1, elapsed_seconds=1.25)
        self.assertIn("AKEUSDT", report)
        self.assertIn("QUIET_ACCUMULATION", report)
        self.assertIn("TRANSIENT_EXECUTION_SPIKE", report)
        self.assertIn("closed breakout with retained execution", report)
        self.assertIn("ليست ضمانًا للصعود", report)

    def test_candle_limit_respects_aligned_endpoint_boundary(self) -> None:
        with self.assertRaises(ValueError):
            build_config({**SETTINGS, "CANDLES": 501})


if __name__ == "__main__":
    unittest.main()
