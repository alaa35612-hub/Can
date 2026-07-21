"""Live scanner, deterministic replay, output and persistence orchestration."""
from __future__ import annotations

import csv
import json
import logging
import math
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
from typing import Iterable, Sequence

from .binance import BinancePublicClient
from .config import ScannerConfig
from .detector import CausalUpsideDetector
from .ledger import LedgerStore
from .models import MarketBar, Readiness, SignalAssessment


READINESS_PRIORITY = {
    Readiness.ARMED: 0,
    Readiness.LIVE_IGNITION: 1,
    Readiness.ACCEPTED: 2,
    Readiness.CONFIRMED_BUILD: 3,
    Readiness.EARLY_BUILD: 4,
    Readiness.CONTINUATION: 5,
    Readiness.COOLING: 6,
    Readiness.LATE_NO_CHASE: 7,
    Readiness.UNRESOLVED: 8,
    Readiness.FAILED: 9,
}


class AtomicOutput:
    @staticmethod
    def write_text(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


class ScannerService:
    def __init__(self, config: ScannerConfig, *, client: BinancePublicClient | None = None):
        self.config = config.validate()
        self.client = client or BinancePublicClient(config)
        self.detector = CausalUpsideDetector(config)
        self.ledger = LedgerStore(config)

    def _analyze(self, symbol: str) -> SignalAssessment | None:
        try:
            fetched = self.client.fetch_symbol(symbol)
            if not fetched.bars:
                return None
            assessment = self.detector.analyze(fetched.bars, source_flags=fetched.flags)
            self.ledger.update(assessment)
            return assessment
        except Exception:
            logging.exception("Symbol analysis failed: %s", symbol)
            return None

    def scan(self, symbols: Sequence[str] | None = None) -> list[SignalAssessment]:
        universe = list(symbols) if symbols is not None else self.client.symbols()
        results: list[SignalAssessment] = []
        with ThreadPoolExecutor(max_workers=self.config.max_workers, thread_name_prefix="upside-scan") as executor:
            futures = {executor.submit(self._analyze, symbol): symbol for symbol in universe}
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    results.append(result)
        results.sort(
            key=lambda item: (
                READINESS_PRIORITY[item.readiness],
                0 if item.entry_safety.startswith("CONDITIONAL") else 1,
                -len(item.supporting_evidence),
                len(item.opposing_evidence),
                item.symbol,
            )
        )
        selected = results[: self.config.top_n]
        self.write_results(selected)
        return selected

    def write_results(self, assessments: Sequence[SignalAssessment]) -> None:
        payload = [item.to_dict() for item in assessments]
        AtomicOutput.write_text(
            self.config.output_dir / "latest_assessments.json",
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        rows = []
        for item in assessments:
            rows.append(
                {
                    "symbol": item.symbol,
                    "timeframe": item.timeframe,
                    "cutoff_ms": item.cutoff_ms,
                    "campaign_state": item.campaign_state.value,
                    "dominant_hypothesis": item.dominant_hypothesis.value,
                    "alternatives": "|".join(value.value for value in item.alternative_hypotheses),
                    "failure_hypothesis": item.failure_hypothesis.value,
                    "structural_bias": item.structural_bias,
                    "signal_importance": item.signal_importance,
                    "readiness": item.readiness.value,
                    "entry_safety": item.entry_safety,
                    "confidence": item.confidence.value,
                    "data_reliability": item.data_reliability.value,
                    "research_status": item.research_status.value,
                    "supporting_evidence": "|".join(value.observation for value in item.supporting_evidence),
                    "opposing_evidence": "|".join(value.observation for value in item.opposing_evidence),
                    "missing_evidence": "|".join(item.missing_evidence),
                    "next_discriminator": item.next_discriminator,
                    "invalidation": item.invalidation,
                    "abstention_reason": item.abstention_reason or "",
                    "quality_flags": "|".join(item.quality_flags),
                }
            )
        if rows:
            import io

            path = self.config.output_dir / "latest_assessments.csv"
            stream = io.StringIO(newline="")
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
            AtomicOutput.write_text(path, stream.getvalue())


class ReplayService:
    """Blind replay through the same production detector path."""

    FIELD_ALIASES = {
        "timestamp_ms": ("timestamp_ms", "timestamp", "open_time"),
        "close_time_ms": ("close_time_ms", "close_time"),
        "is_closed": ("is_closed_candle", "is_closed"),
        "trades": ("number_of_trades", "trades"),
        "quote_volume": ("quote_volume",),
        "taker_buy_quote": ("taker_buy_quote_volume", "taker_buy_quote"),
        "oi": ("oi", "open_interest"),
        "global_ls": ("global_ls_ratio", "global_long_short_ratio", "global_ls", "global_lsr"),
        "top_account_ls": ("acco_ls_ratio", "top_account_long_short_ratio", "top_account_ls", "account_lsr"),
        "top_position_ls": ("posit_ls_ratio", "top_position_long_short_ratio", "top_position_ls", "position_lsr"),
        "funding_rate": ("funding_rate", "last_funding_rate"),
    }

    def __init__(self, config: ScannerConfig):
        replay_config = replace(config.validate(), state_dir=config.state_dir / "replay")
        self.config = replay_config
        self.detector = CausalUpsideDetector(replay_config)

    @staticmethod
    def _number(row: dict[str, str], names: Iterable[str], *, required: bool = False) -> float | None:
        for name in names:
            value = row.get(name)
            if value not in (None, ""):
                try:
                    number = float(value)
                    return number if math.isfinite(number) else None
                except ValueError:
                    continue
        if required:
            raise ValueError(f"Required numeric field missing: {tuple(names)}")
        return None

    @staticmethod
    def _boolean(value: str | None) -> bool:
        return str(value).strip().lower() in {"1", "true", "yes", "y"}

    def load_csv(self, path: Path, *, symbol: str | None = None, timeframe: str | None = None) -> list[MarketBar]:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        bars: list[MarketBar] = []
        for row in rows:
            timestamp = int(self._number(row, self.FIELD_ALIASES["timestamp_ms"], required=True) or 0)
            close_time = int(self._number(row, self.FIELD_ALIASES["close_time_ms"]) or timestamp + self.config.interval_ms - 1)
            closed_value = next((row.get(name) for name in self.FIELD_ALIASES["is_closed"] if name in row), "true")
            if not self._boolean(closed_value):
                continue

            def optional(field: str) -> float | None:
                return self._number(row, self.FIELD_ALIASES[field])

            bars.append(
                MarketBar(
                    symbol=symbol or row.get("symbol") or path.name.split("_")[0],
                    timeframe=timeframe or row.get("timeframe") or self.config.timeframe,
                    timestamp_ms=timestamp,
                    close_time_ms=close_time,
                    is_closed=True,
                    open=float(self._number(row, ("open",), required=True)),
                    high=float(self._number(row, ("high",), required=True)),
                    low=float(self._number(row, ("low",), required=True)),
                    close=float(self._number(row, ("close",), required=True)),
                    volume=self._number(row, ("volume",)),
                    quote_volume=optional("quote_volume"),
                    trades=optional("trades"),
                    taker_buy_quote=optional("taker_buy_quote"),
                    oi=optional("oi"),
                    global_ls=optional("global_ls"),
                    top_account_ls=optional("top_account_ls"),
                    top_position_ls=optional("top_position_ls"),
                    funding_rate=optional("funding_rate"),
                )
            )
        deduplicated = {item.timestamp_ms: item for item in bars}
        return [deduplicated[key] for key in sorted(deduplicated)]

    def run(self, bars: Sequence[MarketBar], output_path: Path) -> list[SignalAssessment]:
        records: list[SignalAssessment] = []
        minimum = max(self.config.min_history, self.config.minimum_baseline_observations + 1)
        for end in range(minimum, len(bars) + 1):
            records.append(self.detector.analyze(bars[:end]))
        AtomicOutput.write_text(
            output_path,
            "".join(json.dumps(item.to_dict(), ensure_ascii=False, sort_keys=True) + "\n" for item in records),
        )
        return records
