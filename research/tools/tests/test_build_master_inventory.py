from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "build_master_inventory.py"
SPEC = importlib.util.spec_from_file_location("build_master_inventory", MODULE_PATH)
assert SPEC and SPEC.loader
inventory = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = inventory
SPEC.loader.exec_module(inventory)

HEADER = [
    "timestamp", "symbol", "is_closed_candle", "open", "high", "low", "close",
    "number_of_trades", "quote_volume", "oi", "oi_value",
]


def row(timestamp: int, close: str = "1", closed: object = True) -> dict[str, object]:
    return {
        "timestamp": timestamp,
        "symbol": "TESTUSDT",
        "is_closed_candle": closed,
        "open": "1",
        "high": "1.1",
        "low": "0.9",
        "close": close,
        "number_of_trades": 10,
        "quote_volume": "100",
        "oi": "50",
        "oi_value": "50",
    }


class InventoryTests(unittest.TestCase):
    def test_csv_jsonl_semantic_equivalence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [row(0), row(900_000, "1.01")]
            stem = "TESTUSDT_15m_limit2_20260101_000000_enriched_candles"
            with (root / f"{stem}.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=HEADER)
                writer.writeheader()
                writer.writerows(rows)
            with (root / f"{stem}.jsonl").open("w", encoding="utf-8") as handle:
                for value in rows:
                    handle.write(json.dumps(value) + "\n")
            output = root / "generated"
            summary = inventory.build(root, output)
            self.assertEqual(summary["csv_jsonl_twin_counts"].get("SEMANTICALLY_EQUIVALENT"), 1)
            report = (output / "CSV_JSONL_TWIN_REPORT.csv").read_text(encoding="utf-8-sig")
            self.assertIn("SEMANTICALLY_EQUIVALENT", report)

    def test_gap_and_unclosed_candle_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "TESTUSDT_15m_limit2_20260101_000000_enriched_candles.csv"
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=HEADER)
                writer.writeheader()
                writer.writerows([row(0), row(1_800_000, closed=False)])
            output = root / "generated"
            inventory.build(root, output)
            manifest = (output / "MASTER_FILE_MANIFEST.csv").read_text(encoding="utf-8-sig")
            self.assertIn("UNCLOSED_CANDLES_PRESENT", manifest)
            self.assertIn("INTRA_FILE_GAPS_OR_INTERVAL_MISMATCH", manifest)

    def test_text_classification_keeps_mixed_sources_separate(self) -> None:
        text = "Xdecow Binance Monitor Bot\nTop OI Gains\nتحليل لماذا ارتفعت العملة والخلاصة"
        self.assertEqual(inventory.classify_text(text, "case.txt"), "MIXED_SOURCE")
        self.assertEqual(inventory.classify_text("هذه قاعدة جديدة", "قاعده.txt"), "RULE_OR_HYPOTHESIS_NOTE")

    def test_interval_relationship_detects_adjacency(self) -> None:
        left = inventory.Record(
            path="a", filename="a", extension="csv", source_class="OBSERVED_MARKET_DATA",
            scope_role="test", first_timestamp_ms=0, last_timestamp_ms=900_000,
            expected_interval_seconds=900,
        )
        right = inventory.Record(
            path="b", filename="b", extension="csv", source_class="OBSERVED_MARKET_DATA",
            scope_role="test", first_timestamp_ms=1_800_000, last_timestamp_ms=2_700_000,
            expected_interval_seconds=900,
        )
        kind, gap = inventory.relation(left, right)
        self.assertEqual(kind, "ADJACENT")
        self.assertEqual(gap, 900)


if __name__ == "__main__":
    unittest.main()
