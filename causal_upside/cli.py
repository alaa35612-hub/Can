"""Command line interface for live scan and causal blind replay."""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import replace
from pathlib import Path

from .config import ScannerConfig
from .service import ReplayService, ScannerService


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Causal Binance Futures upside-precursor research scanner")
    root.add_argument("--timeframe", default="15m")
    root.add_argument("--history-limit", type=int, default=200)
    root.add_argument("--min-history", type=int, default=80)
    root.add_argument("--state-dir", type=Path, default=Path("causal_upside_state"))
    root.add_argument("--output-dir", type=Path, default=Path("causal_upside_output"))
    root.add_argument("--log-level", default="INFO")
    commands = root.add_subparsers(dest="command", required=True)

    scan = commands.add_parser("scan", help="scan current closed Binance Futures bars")
    scan.add_argument("--symbol", action="append", default=[])
    scan.add_argument("--top-n", type=int, default=30)
    scan.add_argument("--workers", type=int, default=8)

    replay = commands.add_parser("replay", help="blind replay an enriched CSV through the production path")
    replay.add_argument("input", type=Path)
    replay.add_argument("--symbol")
    replay.add_argument("--output", type=Path, default=Path("causal_upside_output/replay.jsonl"))
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(message)s")
    config = ScannerConfig(
        timeframe=args.timeframe,
        history_limit=args.history_limit,
        min_history=args.min_history,
        state_dir=args.state_dir,
        output_dir=args.output_dir,
    ).validate()
    if args.command == "scan":
        config = replace(config, top_n=args.top_n, max_workers=args.workers, whitelist=tuple(args.symbol), scan_all_usdt_perpetuals=not bool(args.symbol))
        results = ScannerService(config).scan(args.symbol or None)
        print(json.dumps([item.to_dict() for item in results], ensure_ascii=False, indent=2))
        return 0
    replay = ReplayService(config)
    bars = replay.load_csv(args.input, symbol=args.symbol)
    records = replay.run(bars, args.output)
    summary = {
        "input": str(args.input),
        "closed_bars": len(bars),
        "frozen_cutoffs": len(records),
        "output": str(args.output),
        "last_assessment": records[-1].to_dict() if records else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0
