"""Rate-limited public Binance USD-M Futures ingestion."""
from __future__ import annotations

import json
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from .alignment import attach_series, closed_klines
from .config import ScannerConfig
from .models import MarketBar


BASE_URL = "https://fapi.binance.com"


@dataclass(frozen=True, slots=True)
class FetchResult:
    bars: tuple[MarketBar, ...]
    flags: tuple[str, ...]


class RequestLimiter:
    def __init__(self, requests_per_second: float):
        self.minimum_interval = 1.0 / requests_per_second
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = self.minimum_interval - (now - self._last)
            if delay > 0:
                time.sleep(delay)
            self._last = time.monotonic()


class BinancePublicClient:
    """Network I/O is isolated from all analysis logic."""

    def __init__(self, config: ScannerConfig, *, opener: Callable[..., Any] | None = None):
        self.config = config.validate()
        self._opener = opener or urllib.request.urlopen
        self._limiter = RequestLimiter(self.config.max_requests_per_second)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = urllib.parse.urlencode(params or {})
        url = f"{BASE_URL}{path}{'?' + query if query else ''}"
        last_error: Exception | None = None
        for attempt in range(self.config.retries):
            self._limiter.wait()
            request = urllib.request.Request(url, headers={"User-Agent": "causal-upside-scanner/1.0"})
            try:
                with self._opener(request, timeout=self.config.request_timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                last_error = exc
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                if exc.code not in {418, 429, 500, 502, 503, 504}:
                    break
                delay = float(retry_after) if retry_after else self.config.backoff_base * (2**attempt)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                delay = self.config.backoff_base * (2**attempt)
            time.sleep(delay + random.uniform(0, self.config.backoff_base))
        raise RuntimeError(f"GET {path} failed after {self.config.retries} attempts: {last_error}")

    def symbols(self) -> list[str]:
        payload = self._get("/fapi/v1/exchangeInfo")
        symbols = [
            item["symbol"]
            for item in payload.get("symbols", [])
            if item.get("contractType") == "PERPETUAL"
            and item.get("quoteAsset") == "USDT"
            and item.get("status") == "TRADING"
        ]
        whitelist = set(self.config.whitelist)
        blacklist = set(self.config.blacklist)
        if whitelist:
            symbols = [item for item in symbols if item in whitelist]
        return sorted(item for item in symbols if item not in blacklist)

    @staticmethod
    def _series(payload: Sequence[dict[str, Any]], field: str) -> list[tuple[int, float | None]]:
        output: list[tuple[int, float | None]] = []
        for item in payload:
            try:
                output.append((int(item["timestamp"]), float(item[field])))
            except (KeyError, TypeError, ValueError):
                continue
        return output

    def fetch_symbol(self, symbol: str, *, now_ms: int | None = None) -> FetchResult:
        flags: list[str] = []
        now_ms = int(time.time() * 1000) if now_ms is None else now_ms
        raw_klines = self._get(
            "/fapi/v1/klines",
            {"symbol": symbol, "interval": self.config.timeframe, "limit": self.config.history_limit + 1},
        )
        bars = closed_klines(raw_klines, symbol=symbol, timeframe=self.config.timeframe, now_ms=now_ms)
        if len(bars) > self.config.history_limit:
            bars = bars[-self.config.history_limit :]
        if not bars:
            return FetchResult((), ("KLINES_MISSING",))

        endpoints = {
            "oi": ("/futures/data/openInterestHist", "sumOpenInterest"),
            "global_ls": ("/futures/data/globalLongShortAccountRatio", "longShortRatio"),
            "top_account_ls": ("/futures/data/topLongShortAccountRatio", "longShortRatio"),
            "top_position_ls": ("/futures/data/topLongShortPositionRatio", "longShortRatio"),
        }
        series: dict[str, list[tuple[int, float | None]]] = {}
        for name, (endpoint, field) in endpoints.items():
            try:
                payload = self._get(
                    endpoint,
                    {"symbol": symbol, "period": self.config.timeframe, "limit": self.config.history_limit},
                )
                series[name] = self._series(payload, field)
                if not series[name]:
                    flags.append(f"{name.upper()}_MISSING")
            except RuntimeError as exc:
                series[name] = []
                flags.append(f"{name.upper()}_ENDPOINT_FAILED:{type(exc).__name__}")

        funding_rate = None
        if self.config.include_funding:
            try:
                premium = self._get("/fapi/v1/premiumIndex", {"symbol": symbol})
                funding_rate = float(premium["lastFundingRate"])
            except (RuntimeError, KeyError, TypeError, ValueError):
                flags.append("FUNDING_CONTEXT_MISSING")
        aligned = attach_series(
            bars,
            series,
            max_age_ms=self.config.interval_ms * self.config.max_alignment_age_intervals,
            funding_rate=funding_rate,
        )
        for name in endpoints:
            if all(getattr(item, name) is None for item in aligned):
                flags.append(f"{name.upper()}_ALIGNMENT_EMPTY")
        return FetchResult(tuple(aligned), tuple(sorted(set(flags))))
