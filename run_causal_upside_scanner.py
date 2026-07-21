#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Editor-first runner for the authoritative causal upside scanner.

Edit ``SETTINGS`` below, then press Run in VS Code, PyCharm, IDLE, or any
Python editor. The analytical path remains inside ``causal_upside/`` so live
scanning and historical replay cannot diverge into competing classifiers.
"""
from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from causal_upside.config import ScannerConfig
from causal_upside.models import Readiness, SignalAssessment
from causal_upside.service import ScannerService


# =============================================================================
# EDITOR SETTINGS
# Fixed values here are operational controls only. Structural thresholds remain
# adaptive to each symbol's own causal history inside causal_upside/adaptive.py.
# =============================================================================
SETTINGS: dict[str, Any] = {
    # Execution
    "AUTO_RUN": True,
    "RUN_CONTINUOUSLY": True,
    "SCAN_INTERVAL_SECONDS": 180,

    # Market window
    "TIMEFRAME": "15m",
    "CANDLES": 200,
    "MIN_HISTORY": 80,

    # Universe
    "SCAN_ALL_USDT_PERPETUALS": True,
    "SYMBOL_WHITELIST": [],  # Example: ["AKEUSDT", "TLMUSDT"]
    "SYMBOL_BLACKLIST": ["BTCUSDT", "ETHUSDT"],

    # Runtime and Binance public API
    "MAX_WORKERS": 8,
    "REQUEST_TIMEOUT": 12.0,
    "RETRIES": 3,
    "BACKOFF_BASE": 0.5,
    "MAX_REQUESTS_PER_SECOND": 8.0,
    "INCLUDE_FUNDING": True,
    "MAX_ALIGNMENT_AGE_INTERVALS": 1,

    # Output
    "TOP_N": 30,
    "STATE_DIR": "causal_upside_state",
    "OUTPUT_DIR": "causal_upside_output",
    "PRINT_EVIDENCE_LIMIT": 3,
    "PRINT_MISSING_LIMIT": 4,
    "LOG_LEVEL": "INFO",
}


READINESS_AR = {
    Readiness.ARMED: "مسلح / قريب من الاشتعال",
    Readiness.LIVE_IGNITION: "اشتعال حي",
    Readiness.ACCEPTED: "اشتعال مقبول",
    Readiness.CONFIRMED_BUILD: "بناء مؤكد",
    Readiness.EARLY_BUILD: "بناء مبكر",
    Readiness.CONTINUATION: "استمرار / إعادة تحميل",
    Readiness.COOLING: "تبريد مع بقاء الهيكل",
    Readiness.LATE_NO_CHASE: "متأخر - لا مطاردة",
    Readiness.UNRESOLVED: "غير محسوم",
    Readiness.FAILED: "فشل / توزيع",
}


def _symbols(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip().upper() for value in values if str(value).strip()}))


def build_config(settings: Mapping[str, Any] = SETTINGS) -> ScannerConfig:
    """Translate editor settings into the validated production configuration."""
    history_limit = int(settings["CANDLES"])
    if not 20 <= history_limit <= 500:
        raise ValueError("CANDLES must be between 20 and 500 for aligned Binance history endpoints")
    whitelist = _symbols(settings.get("SYMBOL_WHITELIST", ()))
    scan_all = bool(settings.get("SCAN_ALL_USDT_PERPETUALS", True))
    if not scan_all and not whitelist:
        raise ValueError("Set SYMBOL_WHITELIST when SCAN_ALL_USDT_PERPETUALS is False")
    return ScannerConfig(
        timeframe=str(settings["TIMEFRAME"]),
        history_limit=history_limit,
        min_history=int(settings["MIN_HISTORY"]),
        max_workers=int(settings["MAX_WORKERS"]),
        request_timeout=float(settings["REQUEST_TIMEOUT"]),
        retries=int(settings["RETRIES"]),
        backoff_base=float(settings["BACKOFF_BASE"]),
        max_requests_per_second=float(settings["MAX_REQUESTS_PER_SECOND"]),
        top_n=int(settings["TOP_N"]),
        state_dir=Path(str(settings["STATE_DIR"])),
        output_dir=Path(str(settings["OUTPUT_DIR"])),
        whitelist=whitelist,
        blacklist=_symbols(settings.get("SYMBOL_BLACKLIST", ())),
        scan_all_usdt_perpetuals=scan_all,
        include_funding=bool(settings.get("INCLUDE_FUNDING", True)),
        max_alignment_age_intervals=int(settings.get("MAX_ALIGNMENT_AGE_INTERVALS", 1)),
    ).validate()


def _utc_from_ms(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _short(text: str, limit: int = 150) -> str:
    clean = " ".join(str(text).split())
    return clean if len(clean) <= limit else clean[: limit - 1] + "…"


def _list_text(values: Sequence[str], limit: int, *, empty: str = "لا يوجد") -> str:
    selected = [_short(value) for value in values[: max(0, limit)]]
    return " | ".join(selected) if selected else empty


def assessment_lines(
    item: SignalAssessment,
    rank: int,
    *,
    evidence_limit: int,
    missing_limit: int,
) -> list[str]:
    """Render one explainable assessment without converting it into a trade call."""
    support = [evidence.observation for evidence in item.supporting_evidence]
    oppose = [evidence.observation for evidence in item.opposing_evidence]
    distance = "غير متاح" if item.distance_from_footprint_rank is None else f"{item.distance_from_footprint_rank:.3f}"
    alternatives = ", ".join(value.value for value in item.alternative_hypotheses) or "لا يوجد"
    flags = ", ".join(item.quality_flags) or "لا توجد أعلام جوهرية"
    return [
        f"[{rank:02d}] {item.symbol} | {READINESS_AR[item.readiness]} ({item.readiness.value})",
        f"     الفرضية: {item.dominant_hypothesis.value} | البدائل: {alternatives}",
        f"     الفشل المرجح: {item.failure_hypothesis.value}",
        f"     الانحياز: {item.structural_bias} | الأهمية: {item.signal_importance}",
        f"     أمان الدخول: {item.entry_safety} | الثقة: {item.confidence.value} | موثوقية البيانات: {item.data_reliability.value}",
        f"     عمر الحملة: {item.campaign_age_bars} شمعة | قرب البصمة(rank): {distance} | cutoff: {_utc_from_ms(item.cutoff_ms)}",
        f"     أدلة مؤيدة: {_list_text(support, evidence_limit)}",
        f"     أدلة معارضة: {_list_text(oppose, evidence_limit)}",
        f"     أدلة مفقودة: {_list_text(list(item.missing_evidence), missing_limit)}",
        f"     الدليل التالي المطلوب: {_short(item.next_discriminator, 220)}",
        f"     الإبطال: {_short(item.invalidation, 220)}",
        f"     حالة البحث: {item.research_status.value} | الجودة: {_short(flags, 220)}",
    ] + ([f"     سبب الامتناع: {_short(item.abstention_reason, 220)}"] if item.abstention_reason else [])


def render_console_report(
    assessments: Sequence[SignalAssessment],
    config: ScannerConfig,
    *,
    cycle: int,
    elapsed_seconds: float,
    evidence_limit: int = 3,
    missing_limit: int = 4,
) -> str:
    line = "=" * 118
    scope = "كل عقود USDT الدائمة" if config.scan_all_usdt_perpetuals else ", ".join(config.whitelist)
    output = [
        "",
        line,
        f"ماسح البصمات السابقة للصعود | الدورة {cycle} | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"الفريم={config.timeframe} | الشموع المغلقة={config.history_limit} | الحد الأدنى={config.min_history} | النطاق={scope}",
        f"النتائج المعروضة={len(assessments)}/{config.top_n} | زمن الدورة={elapsed_seconds:.2f}s | المخرجات={config.output_dir}",
        "ملاحظة: النتائج تقييمات بحثية سببية وليست ضمانًا للصعود أو أمر دخول آلي.",
        line,
    ]
    if not assessments:
        output.append("لا توجد نتائج قابلة للتقييم في هذه الدورة. راجع الاتصال، أعلام الجودة، وعدد الشموع.")
        return "\n".join(output)

    for rank, item in enumerate(assessments, start=1):
        output.extend(
            assessment_lines(
                item,
                rank,
                evidence_limit=evidence_limit,
                missing_limit=missing_limit,
            )
        )
        output.append("-" * 118)
    return "\n".join(output)


class EditorScannerRunner:
    """One-process runner that preserves the production service and ledger across cycles."""

    def __init__(self, settings: Mapping[str, Any] = SETTINGS):
        self.settings = dict(settings)
        self.config = build_config(settings)
        self.service = ScannerService(self.config)
        self.explicit_symbols = None if self.config.scan_all_usdt_perpetuals else list(self.config.whitelist)
        self.cycle = 0

    def run_cycle(self) -> list[SignalAssessment]:
        self.cycle += 1
        started = time.monotonic()
        assessments = self.service.scan(self.explicit_symbols)
        elapsed = time.monotonic() - started
        report = render_console_report(
            assessments,
            self.config,
            cycle=self.cycle,
            elapsed_seconds=elapsed,
            evidence_limit=int(self.settings.get("PRINT_EVIDENCE_LIMIT", 3)),
            missing_limit=int(self.settings.get("PRINT_MISSING_LIMIT", 4)),
        )
        print(report, flush=True)
        return assessments

    def run(self) -> None:
        continuous = bool(self.settings.get("RUN_CONTINUOUSLY", True))
        interval = int(self.settings.get("SCAN_INTERVAL_SECONDS", 180))
        if continuous and interval < 1:
            raise ValueError("SCAN_INTERVAL_SECONDS must be at least 1")
        while True:
            cycle_started = time.monotonic()
            self.run_cycle()
            if not continuous:
                return
            remaining = max(0.0, interval - (time.monotonic() - cycle_started))
            next_run = datetime.now(timezone.utc) + timedelta(seconds=remaining)
            print(
                f"الدورة التالية تقريبًا: {next_run.strftime('%Y-%m-%d %H:%M:%S UTC')} | أوقف التشغيل بواسطة Ctrl+C",
                flush=True,
            )
            time.sleep(remaining)


def configure_logging(settings: Mapping[str, Any] = SETTINGS) -> None:
    level_name = str(settings.get("LOG_LEVEL", "INFO")).upper()
    logging.basicConfig(
        level=getattr(logging, level_name, logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )


def main() -> int:
    configure_logging()
    try:
        EditorScannerRunner().run()
    except KeyboardInterrupt:
        print("\nتم إيقاف الماسح يدويًا مع حفظ آخر حالة ومخرجات.")
        return 0
    except Exception as exc:
        logging.exception("تعذر تشغيل الماسح: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    if SETTINGS["AUTO_RUN"]:
        raise SystemExit(main())
    print("AUTO_RUN=False. غيّرها إلى True أو استدعِ main() يدويًا.", file=sys.stderr)
