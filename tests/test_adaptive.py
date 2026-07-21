from __future__ import annotations

import unittest

from causal_upside.adaptive import AdaptiveFeatureEngine
from causal_upside.config import ScannerConfig
from tests.helpers import make_bars


class AdaptiveFeatureTests(unittest.TestCase):
    def test_historical_snapshot_is_suffix_invariant(self) -> None:
        config = ScannerConfig(min_history=30, minimum_baseline_observations=20)
        engine = AdaptiveFeatureEngine(config)
        bars = make_bars(100, breakout=True)
        cutoff = 70
        prefix = engine.snapshot(bars[:cutoff])
        timeline = engine.timeline(bars)
        full_snapshot_at_cutoff = next(item for item in timeline if item.timestamp_ms == bars[cutoff - 1].timestamp_ms)
        self.assertEqual(prefix, full_snapshot_at_cutoff)

    def test_current_value_is_not_inserted_into_its_own_baseline(self) -> None:
        config = ScannerConfig(min_history=30, minimum_baseline_observations=20)
        feature = AdaptiveFeatureEngine(config).snapshot(make_bars(100, breakout=True))
        self.assertGreater(feature.quote_volume.percentile or 0, 0.95)
        self.assertEqual(feature.quote_volume.state, "EXTREME")


if __name__ == "__main__":
    unittest.main()
