#!/usr/bin/env python3
"""Build the standalone editor-first scanner from the authoritative package.

The generated file contains no local-package imports. It is a deterministic
single-file deployment artifact; analytical behavior remains sourced from the
reviewable ``causal_upside`` modules.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "causal_upside_single_file.py"
MODULES = (
    ROOT / "causal_upside/config.py",
    ROOT / "causal_upside/models.py",
    ROOT / "causal_upside/alignment.py",
    ROOT / "causal_upside/binance.py",
    ROOT / "causal_upside/adaptive.py",
    ROOT / "causal_upside/quality.py",
    ROOT / "causal_upside/detector.py",
    ROOT / "causal_upside/ledger.py",
    ROOT / "causal_upside/service.py",
)
RUNNER = ROOT / "run_causal_upside_scanner.py"

PREAMBLE = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Causal Binance USD-M Futures upside-precursor scanner — standalone build.

Generated deterministically from the authoritative ``causal_upside`` package.
Edit SETTINGS near the end of this file and press Run in any Python editor.
Standard-library only; no API keys are required.
"""
from __future__ import annotations

import argparse

'''

STANDALONE_FOOTER = r'''

# =============================================================================
# STANDALONE COMMAND-LINE OVERRIDES AND SELF-TEST
# =============================================================================
def _standalone_self_test() -> None:
    assert bounded_asof([1_000], [(1_001, 7.0)], max_age_ms=100) == [None]
    assert bounded_asof([1_000], [(900, 7.0)], max_age_ms=100) == [7.0]
    raw = [[0, "1", "2", "0.5", "1.5", "10", 999, "15", 4, "0", "8"],
           [1_000, "1.5", "2", "1", "1.8", "11", 2_000, "18", 5, "0", "9"]]
    bars = closed_klines(raw, symbol="TESTUSDT", timeframe="1m", now_ms=1_500)
    assert len(bars) == 1 and bars[0].is_closed
    assert RULE_SCOPE[Hypothesis.SHORT_COVERING_ONLY][0] == RuleStatus.REJECTED_RULE
    ScannerConfig(timeframe="15m", history_limit=80, min_history=40).validate()
    print("SELF-TESTS: PASS")


def standalone_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Standalone causal Binance Futures upside-precursor scanner")
    parser.add_argument("--timeframe", help="Binance interval, e.g. 5m, 15m, 1h, 4h")
    parser.add_argument("--candles", type=int, help="closed candle history, 20..500")
    parser.add_argument("--symbol", action="append", default=[], help="repeat to scan an explicit whitelist")
    parser.add_argument("--once", action="store_true", help="run one scan cycle")
    parser.add_argument("--continuous", action="store_true", help="repeat scan cycles")
    parser.add_argument("--interval", type=int, help="seconds between cycle starts")
    parser.add_argument("--replay", type=Path, help="blind-replay an enriched repository CSV")
    parser.add_argument("--replay-output", type=Path, default=Path("causal_upside_output/replay.jsonl"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _standalone_self_test()
        return 0
    settings = dict(SETTINGS)
    if args.timeframe:
        settings["TIMEFRAME"] = args.timeframe
    if args.candles is not None:
        settings["CANDLES"] = args.candles
    if args.symbol:
        settings["SCAN_ALL_USDT_PERPETUALS"] = False
        settings["SYMBOL_WHITELIST"] = [value.upper() for value in args.symbol]
    if args.once:
        settings["RUN_CONTINUOUSLY"] = False
    if args.continuous:
        settings["RUN_CONTINUOUSLY"] = True
    if args.interval is not None:
        settings["SCAN_INTERVAL_SECONDS"] = args.interval
    configure_logging(settings)
    if args.replay:
        config = build_config(settings)
        replay = ReplayService(config)
        bars = replay.load_csv(args.replay, timeframe=config.timeframe)
        records = replay.run(bars, args.replay_output)
        summary = {
            "input": str(args.replay),
            "closed_bars": len(bars),
            "frozen_cutoffs": len(records),
            "output": str(args.replay_output),
            "last_assessment": records[-1].to_dict() if records else None,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    try:
        EditorScannerRunner(settings).run()
    except KeyboardInterrupt:
        print("\nتم إيقاف الماسح يدويًا مع حفظ آخر حالة ومخرجات.")
        return 0
    return 0


if __name__ == "__main__":
    if SETTINGS.get("AUTO_RUN", True) or len(sys.argv) > 1:
        raise SystemExit(standalone_cli())
    print("AUTO_RUN=False. غيّرها إلى True أو استدعِ standalone_cli() يدويًا.", file=sys.stderr)
'''

BUILD_META = '''

# =============================================================================
# GENERATED BUILD METADATA
# =============================================================================
STANDALONE_BUILD = {
    "generator": "tools/build_single_file_scanner.py",
    "source_modules": %r,
    "warning": "Generated file. Edit SETTINGS only; change analytical logic in causal_upside/.",
}
'''


def strip_module(source: str) -> str:
    """Remove package-only imports and module-level docstrings/future imports."""
    source = source.replace("\r\n", "\n")
    source = re.sub(r"\A\s*(?:[rubfRUBF]*)(?:'''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\")\s*", "", source, count=1)
    lines = source.splitlines()
    output: list[str] = []
    skipping_relative = False
    paren_depth = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("from __future__ import"):
            continue
        if skipping_relative:
            paren_depth += line.count("(") - line.count(")")
            if paren_depth <= 0:
                skipping_relative = False
            continue
        if stripped.startswith("from ."):
            paren_depth = line.count("(") - line.count(")")
            skipping_relative = paren_depth > 0
            continue
        output.append(line)
    return "\n".join(output).strip() + "\n"


def strip_runner(source: str) -> str:
    source = source.replace("\r\n", "\n")
    source = re.sub(r"\A#!.*\n", "", source)
    source = re.sub(r"\A\s*#.*coding[:=].*\n", "", source)
    source = re.sub(r"\A\s*(?:[rubfRUBF]*)(?:'''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\")\s*", "", source, count=1)
    lines = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("if __name__ == \"__main__\":"):
            break
        if stripped.startswith("from __future__ import"):
            continue
        if stripped.startswith("from causal_upside."):
            continue
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def build_text() -> str:
    missing = [str(path.relative_to(ROOT)) for path in (*MODULES, RUNNER) if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing source files: " + ", ".join(missing))
    sections = [PREAMBLE]
    for path in MODULES:
        sections.append(
            "\n# " + "=" * 77 + "\n"
            f"# SOURCE: {path.relative_to(ROOT).as_posix()}\n"
            "# " + "=" * 77 + "\n"
        )
        sections.append(strip_module(path.read_text(encoding="utf-8")))
    sections.append(
        "\n# " + "=" * 77 + "\n"
        "# EDITOR-FIRST SETTINGS, ARABIC OUTPUT, AND AUTO-RUN\n"
        "# " + "=" * 77 + "\n"
    )
    sections.append(strip_runner(RUNNER.read_text(encoding="utf-8")))
    sections.append(STANDALONE_FOOTER)
    names = tuple(path.relative_to(ROOT).as_posix() for path in (*MODULES, RUNNER))
    sections.append(BUILD_META % (names,))
    text = "".join(sections)
    return text.rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when the checked-in standalone file is stale")
    parser.add_argument("--stdout", action="store_true", help="write generated text to stdout")
    args = parser.parse_args(argv)
    text = build_text()
    if args.stdout:
        sys.stdout.write(text)
        return 0
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != text:
            print(f"{OUTPUT.relative_to(ROOT)} is stale; run {Path(__file__).relative_to(ROOT)}", file=sys.stderr)
            return 1
        print(f"standalone up to date: sha256={hashlib.sha256(text.encode()).hexdigest()}")
        return 0
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"generated {OUTPUT.relative_to(ROOT)} | bytes={len(text.encode())} | sha256={hashlib.sha256(text.encode()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
