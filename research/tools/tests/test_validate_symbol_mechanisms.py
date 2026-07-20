from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_symbol_mechanisms.py"
SPEC = importlib.util.spec_from_file_location("validate_symbol_mechanisms", MODULE_PATH)
assert SPEC and SPEC.loader
VALIDATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATE)


def row(source: str, close: float = 100.0, rsi: float = 50.0, trades: float = 1000.0):
    return {
        "timeframe": "15m",
        "timestamp": 0,
        "source": source,
        "close": close,
        "rsi": rsi,
        "number_of_trades": trades,
        "quote_volume": 10000.0,
        "avg_quote_per_trade": 10.0,
        "taker_quote_imbalance_pct": 0.0,
        "oi": 100000.0,
        "oi_value": 1000000.0,
        "acco_ls_ratio": 1.0,
        "posit_ls_ratio": 1.0,
        "global_ls_ratio": 1.0,
        "funding_rate": 0.0,
    }


class SourceSelectionTests(unittest.TestCase):
    def test_earliest_and_latest_capture(self):
        group = [row("SYMBOL_20260718.csv"), row("SYMBOL_20260719.csv")]
        self.assertEqual(
            VALIDATE.select_source_row(group, "EARLIEST_CAPTURE")["source"],
            "SYMBOL_20260718.csv",
        )
        self.assertEqual(
            VALIDATE.select_source_row(group, "LATEST_CAPTURE")["source"],
            "SYMBOL_20260719.csv",
        )

    def test_rsi_only_conflict_is_not_decision_relevant(self):
        rows = [row("a.csv", rsi=40.0), row("b.csv", rsi=60.0)]
        summary = VALIDATE.conflict_field_summary(rows)
        self.assertEqual(summary["material_conflict_groups"], 1)
        self.assertEqual(summary["decision_relevant_conflict_groups"], 0)
        self.assertEqual(summary["field_counts"], {"rsi": 1})

    def test_close_conflict_is_decision_relevant(self):
        rows = [row("a.csv", close=100.0), row("b.csv", close=101.0)]
        summary = VALIDATE.conflict_field_summary(rows)
        self.assertEqual(summary["decision_relevant_conflict_groups"], 1)
        self.assertEqual(summary["field_counts"], {"close": 1})


class NegativeControlTests(unittest.TestCase):
    def test_direct_and_descendant_rejections_are_retained(self):
        reviewed = [
            {
                "timestamp": 1,
                "to_state": "ACCEPTED_IGNITION",
                "adversarial_status": "REJECT",
                "effective_status": "REJECT",
                "adversarial_reasons": ["negative price dislocation"],
            },
            {
                "timestamp": 2,
                "to_state": "EXPANSION",
                "adversarial_status": "REJECT",
                "effective_status": "REJECT",
                "adversarial_reasons": ["transition depends on an unvalidated predecessor"],
            },
            {
                "timestamp": 3,
                "to_state": "EARLY_BUILD",
                "adversarial_status": "PASS",
                "effective_status": "PASS",
            },
        ]
        anchors = VALIDATE.negative_control_anchors(reviewed)
        self.assertEqual(len(anchors), 2)
        self.assertEqual(anchors[0]["negative_control_type"], "DIRECT_REJECTED_TRANSITION")
        self.assertEqual(anchors[1]["negative_control_type"], "REJECTED_DESCENDANT")


class MechanismMetricTests(unittest.TestCase):
    def test_leading_mechanism_preserves_simultaneous_evidence(self):
        transitions = [
            {
                "timestamp": 10,
                "effective_status": "PASS",
                "facts_added": ["oi_expansion", "execution_expansion"],
            },
            {
                "timestamp": 20,
                "effective_status": "PASS",
                "facts_added": ["positive_price_release"],
            },
        ]
        self.assertEqual(
            VALIDATE.leading_mechanism(transitions),
            "EXECUTION_AND_OI_SIMULTANEOUS",
        )

    def test_reset_depth_is_not_measured_across_gap(self):
        rows = [
            {"timestamp": 0, "close": 100.0, "oi": 1000.0},
            {"timestamp": 900_000, "close": 101.0, "oi": 1100.0},
            {"timestamp": 10_000_000, "close": 90.0, "oi": 900.0},
        ]
        previous = {
            "start": VALIDATE.ms_to_iso(0),
            "end": VALIDATE.ms_to_iso(900_000),
        }
        result = VALIDATE.reset_depth(rows, previous, 10_000_000)
        self.assertEqual(result["reset_depth_status"], "UNOBSERVED_GAP")
        self.assertIsNone(result["price_reset_depth_pct"])

    def test_reset_depth_uses_observed_prior_peak(self):
        rows = [
            {"timestamp": 0, "close": 100.0, "oi": 1000.0},
            {"timestamp": 900_000, "close": 120.0, "oi": 1500.0},
            {"timestamp": 1_800_000, "close": 108.0, "oi": 1200.0},
        ]
        previous = {
            "start": VALIDATE.ms_to_iso(0),
            "end": VALIDATE.ms_to_iso(900_000),
        }
        result = VALIDATE.reset_depth(rows, previous, 1_800_000)
        self.assertEqual(result["reset_depth_status"], "MEASURED")
        self.assertAlmostEqual(result["price_reset_depth_pct"], -10.0)
        self.assertAlmostEqual(result["oi_reset_depth_pct"], -20.0)


if __name__ == "__main__":
    unittest.main()
