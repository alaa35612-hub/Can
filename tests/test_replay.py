from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from causal_upside.config import ScannerConfig
from causal_upside.service import ReplayService
from tests.helpers import make_bars


class ReplayTests(unittest.TestCase):
    def test_repository_enriched_schema_aliases_are_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AKEUSDT_15m_sample.csv"
            fields = ["timestamp", "close_time", "is_closed_candle", "symbol", "open", "high", "low", "close", "volume", "quote_volume", "number_of_trades", "taker_buy_quote_volume", "oi", "acco_ls_ratio", "posit_ls_ratio", "global_ls_ratio", "funding_rate"]
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"timestamp": 1, "close_time": 2, "is_closed_candle": "True", "symbol": "AKEUSDT", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10, "quote_volume": 15, "number_of_trades": 4, "taker_buy_quote_volume": 8, "oi": 100, "acco_ls_ratio": 1.1, "posit_ls_ratio": 1.2, "global_ls_ratio": 0.9, "funding_rate": 0.0001})
            loaded = ReplayService(ScannerConfig(min_history=20)).load_csv(path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].top_account_ls, 1.1)
            self.assertEqual(loaded[0].top_position_ls, 1.2)
            self.assertEqual(loaded[0].global_ls, 0.9)

    def test_replay_freezes_each_cutoff_and_writes_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "TESTUSDT_15m_enriched_candles.csv"
            bars = make_bars(70, breakout=True)
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(bars[0].to_dict()))
                writer.writeheader()
                for bar in bars:
                    row = bar.to_dict()
                    row["is_closed"] = "true"
                    writer.writerow(row)
            config = ScannerConfig(min_history=30, minimum_baseline_observations=20, state_dir=root / "state")
            replay = ReplayService(config)
            loaded = replay.load_csv(source)
            output = root / "replay.jsonl"
            records = replay.run(loaded, output)
            self.assertEqual(len(records), len(loaded) - config.min_history + 1)
            lines = output.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), len(records))
            self.assertTrue(all(json.loads(line)["cutoff_ms"] for line in lines))


if __name__ == "__main__":
    unittest.main()
