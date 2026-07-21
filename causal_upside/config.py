"""Validated operational configuration."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


TIMEFRAME_MS = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "2h": 7_200_000,
    "4h": 14_400_000,
    "6h": 21_600_000,
    "8h": 28_800_000,
    "12h": 43_200_000,
    "1d": 86_400_000,
}


@dataclass(frozen=True, slots=True)
class ScannerConfig:
    timeframe: str = "15m"
    history_limit: int = 200
    min_history: int = 80
    max_workers: int = 8
    request_timeout: float = 12.0
    retries: int = 3
    backoff_base: float = 0.5
    max_requests_per_second: float = 8.0
    top_n: int = 30
    state_dir: Path = Path("causal_upside_state")
    output_dir: Path = Path("causal_upside_output")
    whitelist: tuple[str, ...] = ()
    blacklist: tuple[str, ...] = ("BTCUSDT", "ETHUSDT")
    scan_all_usdt_perpetuals: bool = True
    include_funding: bool = True
    adaptive_quantiles: tuple[float, float, float] = (0.75, 0.90, 0.975)
    minimum_baseline_observations: int = 24
    max_alignment_age_intervals: int = 1
    ledger_schema_version: int = 1

    def validate(self) -> "ScannerConfig":
        if self.timeframe not in TIMEFRAME_MS:
            raise ValueError(f"Unsupported timeframe: {self.timeframe}")
        if self.history_limit < self.min_history:
            raise ValueError("history_limit must be >= min_history")
        if self.min_history < 20:
            raise ValueError("min_history must be at least 20 closed bars")
        if not 1 <= self.max_workers <= 32:
            raise ValueError("max_workers must be between 1 and 32")
        if self.retries < 1:
            raise ValueError("retries must be positive")
        if self.max_requests_per_second <= 0:
            raise ValueError("max_requests_per_second must be positive")
        if tuple(sorted(self.adaptive_quantiles)) != self.adaptive_quantiles:
            raise ValueError("adaptive_quantiles must be increasing")
        if any(not 0 < item < 1 for item in self.adaptive_quantiles):
            raise ValueError("adaptive_quantiles must be inside (0, 1)")
        return self

    @property
    def interval_ms(self) -> int:
        return TIMEFRAME_MS[self.timeframe]
