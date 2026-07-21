"""Causal market-data validation and confidence caps."""
from __future__ import annotations

import math
from collections import Counter
from typing import Sequence

from .config import ScannerConfig
from .models import Confidence, MarketBar, QualityReport, Reliability


class DataQualityChecker:
    def __init__(self, config: ScannerConfig):
        self.config = config.validate()

    def check(self, bars: Sequence[MarketBar], *, source_flags: Sequence[str] = ()) -> QualityReport:
        flags = list(source_flags)
        if not bars:
            return QualityReport(tuple(sorted(set(flags + ["NO_BARS"]))), Reliability.UNUSABLE, Confidence.LOW, False, 0, self.config.interval_ms)

        ordered = list(bars)
        timestamps = [item.timestamp_ms for item in ordered]
        closed = [item for item in ordered if item.is_closed]
        if len(closed) != len(ordered):
            flags.append("OPEN_CANDLE_PRESENT")
        if len(closed) < self.config.min_history:
            flags.append("INSUFFICIENT_CLOSED_HISTORY")
        if timestamps != sorted(timestamps):
            flags.append("NON_MONOTONIC_TIMESTAMPS")
        duplicate_count = len(timestamps) - len(set(timestamps))
        if duplicate_count:
            flags.append(f"DUPLICATE_TIMESTAMPS:{duplicate_count}")
        gaps = [right - left for left, right in zip(timestamps, timestamps[1:])]
        irregular = sum(delta != self.config.interval_ms for delta in gaps)
        if irregular:
            flags.append(f"IRREGULAR_INTERVALS:{irregular}")
        for item in ordered:
            numeric = (item.open, item.high, item.low, item.close)
            if any(not math.isfinite(value) or value <= 0 for value in numeric):
                flags.append("INVALID_OHLC")
                break
            if not item.low <= min(item.open, item.close) <= max(item.open, item.close) <= item.high:
                flags.append("INCONSISTENT_OHLC")
                break
        missing = Counter()
        for item in ordered:
            for field in ("quote_volume", "trades", "oi", "global_ls", "top_account_ls", "top_position_ls"):
                value = getattr(item, field)
                if value is None or not math.isfinite(value):
                    missing[field] += 1
        for field, count in missing.items():
            if count == len(ordered):
                flags.append(f"{field.upper()}_MISSING")
            elif count:
                flags.append(f"{field.upper()}_PARTIAL:{count}")

        unique = set(flags)
        fatal = any(flag.startswith(("NO_BARS", "NON_MONOTONIC", "INVALID_OHLC", "INCONSISTENT_OHLC")) for flag in unique)
        major = sum(
            flag.startswith(("INSUFFICIENT", "OPEN_CANDLE", "DUPLICATE", "IRREGULAR", "OI_MISSING", "QUOTE_VOLUME_MISSING", "TRADES_MISSING"))
            for flag in unique
        )
        if fatal:
            reliability = Reliability.UNUSABLE
            cap = Confidence.LOW
        elif major >= 3:
            reliability = Reliability.LOW
            cap = Confidence.LOW
        elif major or len(unique) >= 4:
            reliability = Reliability.MEDIUM
            cap = Confidence.MEDIUM
        else:
            reliability = Reliability.HIGH
            cap = Confidence.HIGH
        return QualityReport(tuple(sorted(unique)), reliability, cap, not fatal and len(closed) >= 2, len(closed), self.config.interval_ms)
