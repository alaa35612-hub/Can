from __future__ import annotations

import unittest

from causal_upside.alignment import bounded_asof, closed_klines


class AlignmentTests(unittest.TestCase):
    def test_bounded_asof_never_uses_future_or_stale_value(self) -> None:
        values = bounded_asof([100, 200, 400], [(150, 1.0), (200, 2.0)], max_age_ms=100)
        self.assertEqual(values, [None, 2.0, None])

    def test_open_kline_is_excluded(self) -> None:
        raw = [
            [0, "1", "2", "0.5", "1.5", "10", 99, "15", 4, "0", "8"],
            [100, "1.5", "2.5", "1", "2", "12", 250, "20", 5, "0", "11"],
        ]
        bars = closed_klines(raw, symbol="XUSDT", timeframe="1m", now_ms=200)
        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0].timestamp_ms, 0)


if __name__ == "__main__":
    unittest.main()
