#!/usr/bin/env python3
"""Build a causal, auditable inventory of the repository research corpus.

Standard-library only. Source evidence is read-only; all generated files are
written below research/inventory/generated unless another directory is passed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Iterator

MARKET_RE = re.compile(
    r"(?P<symbol>[A-Z0-9]+USDT)_(?P<tf>5m|15m|1h|4h|1d)_limit(?P<limit>\d+)_"
    r"(?P<capture>\d{8}_\d{6})_enriched_candles\.(?P<ext>csv|jsonl)$"
)
SYMBOL_RE = re.compile(r"\b[A-Z0-9]{2,24}USDT\b")
TF_SECONDS = {"5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}
CRITICAL = {
    "timestamp", "symbol", "is_closed_candle", "open", "high", "low", "close",
    "number_of_trades", "quote_volume", "oi", "oi_value",
}
EXCLUDED_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


@dataclass
class Record:
    path: str
    filename: str
    extension: str
    source_class: str
    scope_role: str
    symbol: str = ""
    linked_symbols: str = ""
    timeframe: str = ""
    nominal_limit: str = ""
    capture_time: str = ""
    byte_size: int = 0
    raw_sha256: str = ""
    actual_rows: int | None = None
    line_count: int | None = None
    first_timestamp_ms: int | None = None
    last_timestamp_ms: int | None = None
    first_time_utc: str = ""
    last_time_utc: str = ""
    closed_true_count: int | None = None
    closed_false_count: int | None = None
    closed_missing_count: int | None = None
    chronological_strict: str = ""
    duplicate_timestamp_count: int | None = None
    gap_count: int | None = None
    expected_interval_seconds: int | None = None
    schema_column_count: int | None = None
    schema_hash: str = ""
    semantic_row_hash: str = ""
    parse_encoding: str = ""
    parse_status: str = "PENDING"
    twin_path: str = ""
    twin_status: str = "NOT_APPLICABLE"
    quality_status: str = "PENDING"
    quality_flags: str = ""
    extraction_status: str = ""
    notes: str = ""
    _row_hashes: list[str] = field(default_factory=list, repr=False)

    def public(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("_row_hashes", None)
        return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value).strip()
    if text.lower() in {"true", "false"}:
        return text.lower()
    if not text:
        return ""
    try:
        number = Decimal(text)
        if not number.is_finite():
            return text.lower()
        if number == 0:
            return "0"
        return format(number.normalize(), "f")
    except (InvalidOperation, ValueError):
        return text


def row_hash(row: dict[str, Any], columns: Iterable[str]) -> str:
    payload = [(key, normalize(row.get(key))) for key in sorted(columns)]
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def parse_timestamp(row: dict[str, Any]) -> int | None:
    for key in ("timestamp", "open_time"):
        value = row.get(key)
        if value not in (None, ""):
            try:
                return int(Decimal(str(value)))
            except (InvalidOperation, ValueError):
                continue
    return None


def utc(ms: int | None) -> str:
    if ms is None:
        return ""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def scope(path: Path) -> str:
    posix = path.as_posix()
    if posix.startswith("research/"):
        return "RESEARCH_LAYER"
    if posix.startswith(".claude/") or posix == "BLACK_JOHN_RESEARCH_SKILLS.md":
        return "SKILLS_LAYER"
    if posix.startswith(".github/"):
        return "AUTOMATION"
    if path.suffix.lower() in {".py", ".js", ".ts", ".toml", ".yaml", ".yml"}:
        return "IMPLEMENTATION_OR_CONFIG"
    return "CORPUS_OR_PROJECT_SOURCE"


def files(root: Path, output: Path) -> Iterator[Path]:
    output = output.resolve()
    for current, dirs, names in os.walk(root):
        current_path = Path(current)
        dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRS]
        resolved = current_path.resolve()
        if resolved == output or output in resolved.parents:
            dirs[:] = []
            continue
        for name in names:
            yield current_path / name


def csv_rows(path: Path) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), tuple(reader.fieldnames or ())


def jsonl_rows(path: Path) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    rows: list[dict[str, Any]] = []
    columns: set[str] = set()
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"line {line_number}: JSON object required")
            rows.append(value)
            columns.update(value)
    return rows, tuple(sorted(columns))


def audit_market(path: Path, rel: Path, match: re.Match[str]) -> Record:
    info = match.groupdict()
    record = Record(
        path=rel.as_posix(), filename=path.name, extension=info["ext"],
        source_class="OBSERVED_MARKET_DATA", scope_role=scope(rel),
        symbol=info["symbol"], linked_symbols=info["symbol"], timeframe=info["tf"],
        nominal_limit=info["limit"],
        capture_time=datetime.strptime(info["capture"], "%Y%m%d_%H%M%S")
        .replace(tzinfo=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        byte_size=path.stat().st_size, raw_sha256=sha256_file(path),
        expected_interval_seconds=TF_SECONDS[info["tf"]], parse_encoding="utf-8-sig",
    )
    flags: list[str] = []
    try:
        rows, columns = csv_rows(path) if info["ext"] == "csv" else jsonl_rows(path)
        all_columns = set(columns)
        for row in rows:
            all_columns.update(row)
        canonical_columns = tuple(sorted(all_columns))
        record.schema_column_count = len(canonical_columns)
        record.schema_hash = hashlib.sha256("\n".join(canonical_columns).encode()).hexdigest()
        record.actual_rows = len(rows)
        timestamps: list[int] = []
        true_count = false_count = missing_count = 0
        hashes: list[str] = []
        for row in rows:
            timestamp = parse_timestamp(row)
            if timestamp is not None:
                timestamps.append(timestamp)
            closed = parse_bool(row.get("is_closed_candle"))
            if closed is True:
                true_count += 1
            elif closed is False:
                false_count += 1
            else:
                missing_count += 1
            hashes.append(row_hash(row, canonical_columns))
        record._row_hashes = hashes
        stream = hashlib.sha256()
        for digest in hashes:
            stream.update(digest.encode("ascii") + b"\n")
        record.semantic_row_hash = stream.hexdigest()
        record.closed_true_count = true_count
        record.closed_false_count = false_count
        record.closed_missing_count = missing_count
        if timestamps:
            record.first_timestamp_ms, record.last_timestamp_ms = timestamps[0], timestamps[-1]
            record.first_time_utc, record.last_time_utc = utc(timestamps[0]), utc(timestamps[-1])
        record.duplicate_timestamp_count = len(timestamps) - len(set(timestamps))
        record.chronological_strict = str(all(b > a for a, b in zip(timestamps, timestamps[1:])))
        expected = record.expected_interval_seconds * 1000
        record.gap_count = sum(1 for a, b in zip(timestamps, timestamps[1:]) if b - a != expected)
        missing_fields = sorted(CRITICAL - all_columns)
        if record.actual_rows == 0:
            flags.append("EMPTY_MARKET_FILE")
        if false_count:
            flags.append("UNCLOSED_CANDLES_PRESENT")
        if missing_count:
            flags.append("CLOSED_STATE_MISSING")
        if record.duplicate_timestamp_count:
            flags.append("DUPLICATE_TIMESTAMPS")
        if record.chronological_strict != "True":
            flags.append("NON_STRICT_CHRONOLOGY")
        if record.gap_count:
            flags.append("INTRA_FILE_GAPS_OR_INTERVAL_MISMATCH")
        if missing_fields:
            flags.append("MISSING_CRITICAL_FIELDS:" + "|".join(missing_fields))
        if record.actual_rows != int(info["limit"]):
            flags.append("NOMINAL_LIMIT_DIFFERS_FROM_ACTUAL_ROWS")
        record.parse_status = "PARSED"
        if record.actual_rows == 0 or false_count or record.chronological_strict != "True":
            record.quality_status = "LOW"
        elif record.gap_count or missing_fields or (record.actual_rows or 0) < 20:
            record.quality_status = "MEDIUM"
        else:
            record.quality_status = "HIGH"
    except Exception as exc:  # manifest must preserve failures
        record.parse_status = "FAILED"
        record.quality_status = "UNUSABLE"
        flags.append(f"PARSE_ERROR:{type(exc).__name__}:{exc}")
    record.quality_flags = ";".join(flags)
    return record


def decode_text(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1256", "windows-1252", "latin-1"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8-replace"


def classify_text(text: str, filename: str) -> str:
    lower = text.lower()
    raw_markers = (
        "xdecow binance monitor bot", "top oi gains", "top open interest",
        "long/short ratio changes", "top number of trades", "increase in trades",
    )
    analysis_markers = (
        "تحليل", "القاعدة", "الخلاصة", "الفرضية", "لماذا", "super prompt",
        "research hypothesis", "state ledger",
    )
    raw_hits = sum(marker in lower for marker in raw_markers)
    analysis_hits = sum(marker in lower for marker in analysis_markers)
    filename_rule = any(marker in filename.lower() for marker in ("قاعدة", "قاعده", "قواعد", "شرح نظري", "prompt"))
    if raw_hits and analysis_hits:
        return "MIXED_SOURCE"
    if raw_hits:
        return "RAW_MONITOR_EXPORT"
    if filename_rule or "super prompt" in lower or "القاعدة الجديدة" in lower:
        return "RULE_OR_HYPOTHESIS_NOTE"
    return "PRIOR_ANALYSIS"


def audit_other(path: Path, rel: Path) -> Record:
    ext = path.suffix.lower().lstrip(".")
    record = Record(
        path=rel.as_posix(), filename=path.name, extension=ext,
        source_class="UNKNOWN", scope_role=scope(rel), byte_size=path.stat().st_size,
        raw_sha256=sha256_file(path),
    )
    if ext in {"txt", "md"}:
        text, encoding = decode_text(path)
        record.linked_symbols = ";".join(sorted(set(SYMBOL_RE.findall(text)) | set(SYMBOL_RE.findall(path.name))))
        record.line_count = len(text.splitlines())
        record.parse_encoding = encoding
        record.source_class = classify_text(text, path.name) if ext == "txt" else "DOCUMENTATION"
        record.parse_status = "PARSED"
        record.quality_status = "NOT_APPLICABLE"
        record.extraction_status = "TEXT_AVAILABLE"
    elif ext in {"doc", "docx", "pdf"}:
        record.linked_symbols = ";".join(sorted(set(SYMBOL_RE.findall(path.name))))
        record.source_class = "BINARY_LEGACY_DOCUMENT"
        record.parse_status = "METADATA_ONLY"
        record.quality_status = "PENDING_EXTRACTION"
        record.extraction_status = "PENDING_SEPARATE_DERIVATIVE"
        record.quality_flags = "SEMANTIC_CONTENT_NOT_INSPECTED"
    elif ext in {"py", "js", "ts", "tsx", "jsx", "sh", "ps1"}:
        record.source_class, record.parse_status, record.quality_status = "IMPLEMENTATION", "METADATA_ONLY", "NOT_APPLICABLE"
    elif ext in {"yaml", "yml", "toml", "json"}:
        record.source_class, record.parse_status, record.quality_status = "CONFIG_OR_STRUCTURED_DOCUMENT", "METADATA_ONLY", "NOT_APPLICABLE"
    elif ext in {"csv", "jsonl"}:
        record.source_class, record.parse_status, record.quality_status = "GENERATED_OR_UNRECOGNIZED_TABULAR_DATA", "METADATA_ONLY", "PENDING_REVIEW"
    else:
        record.source_class, record.parse_status, record.quality_status = "OTHER_REPOSITORY_FILE", "METADATA_ONLY", "NOT_APPLICABLE"
    return record


def relation(a: Record, b: Record) -> tuple[str, int | None]:
    if None in (a.first_timestamp_ms, a.last_timestamp_ms, b.first_timestamp_ms, b.last_timestamp_ms):
        return "UNKNOWN", None
    a0, a1, b0, b1 = int(a.first_timestamp_ms), int(a.last_timestamp_ms), int(b.first_timestamp_ms), int(b.last_timestamp_ms)
    if a0 == b0 and a1 == b1:
        return "EXACT_COVERAGE", 0
    if a0 <= b0 and a1 >= b1:
        return "A_CONTAINS_B", 0
    if b0 <= a0 and b1 >= a1:
        return "B_CONTAINS_A", 0
    if max(a0, b0) <= min(a1, b1):
        return "PARTIAL_OVERLAP", (min(a1, b1) - max(a0, b0)) // 1000
    earlier, later = (a, b) if a1 < b0 else (b, a)
    gap = int(later.first_timestamp_ms) - int(earlier.last_timestamp_ms)
    expected = (a.expected_interval_seconds or b.expected_interval_seconds or 0) * 1000
    return ("ADJACENT" if expected and gap == expected else "GAP"), gap // 1000


def apply_twins(records: list[Record]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Record]] = defaultdict(dict)
    for record in records:
        if record.source_class == "OBSERVED_MARKET_DATA":
            grouped[str(Path(record.path).with_suffix(""))][record.extension] = record
    results: list[dict[str, Any]] = []
    for stem, variants in sorted(grouped.items()):
        left, right = variants.get("csv"), variants.get("jsonl")
        if not left or not right:
            continue
        left.twin_path, right.twin_path = right.path, left.path
        if left.parse_status != "PARSED" or right.parse_status != "PARSED":
            status = "UNRESOLVED_PARSE_FAILURE"
        elif left.actual_rows != right.actual_rows:
            status = "ROW_COUNT_MISMATCH"
        elif left.schema_hash != right.schema_hash:
            status = "SCHEMA_MISMATCH"
        elif left._row_hashes != right._row_hashes:
            status = "ROW_CONTENT_MISMATCH"
        else:
            status = "SEMANTICALLY_EQUIVALENT"
        left.twin_status = right.twin_status = status
        if status != "SEMANTICALLY_EQUIVALENT":
            for record in (left, right):
                flags = [flag for flag in record.quality_flags.split(";") if flag]
                flags.append("CSV_JSONL_TWIN_" + status)
                record.quality_flags = ";".join(flags)
                if record.quality_status == "HIGH":
                    record.quality_status = "MEDIUM"
        results.append({
            "stem": stem, "csv_path": left.path, "jsonl_path": right.path,
            "status": status, "csv_rows": left.actual_rows, "jsonl_rows": right.actual_rows,
            "csv_schema_hash": left.schema_hash, "jsonl_schema_hash": right.schema_hash,
        })
    return results


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(buffer.getvalue(), encoding="utf-8-sig")


def table(headers: list[str], rows: Iterable[Iterable[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        values = [str(value).replace("|", "\\|").replace("\n", " ") for value in row]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build(root: Path, output: Path) -> dict[str, Any]:
    root, output = root.resolve(), output.resolve()
    records: list[Record] = []
    for path in sorted(files(root, output)):
        rel = path.resolve().relative_to(root)
        match = MARKET_RE.fullmatch(path.name)
        records.append(audit_market(path, rel, match) if match else audit_other(path, rel))

    twins = apply_twins(records)
    public = [record.public() for record in records]
    write_csv(output / "MASTER_FILE_MANIFEST.csv", public, list(public[0]) if public else ["path"])
    if twins:
        write_csv(output / "CSV_JSONL_TWIN_REPORT.csv", twins, list(twins[0]))

    market = [record for record in records if record.source_class == "OBSERVED_MARKET_DATA"]
    documents = [record for record in records if record.source_class in {
        "PRIOR_ANALYSIS", "RULE_OR_HYPOTHESIS_NOTE", "RAW_MONITOR_EXPORT", "MIXED_SOURCE", "BINARY_LEGACY_DOCUMENT",
    }]
    quality = Counter(record.quality_status for record in market)
    classes = Counter(record.source_class for record in records)
    timeframes = Counter(record.timeframe for record in market)

    symbol_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in market:
        symbol_counts[record.symbol][record.timeframe] += 1
        symbol_counts[record.symbol][record.extension] += 1
        symbol_counts[record.symbol]["total"] += 1
    symbol_rows: list[dict[str, Any]] = []
    for symbol, counts in sorted(symbol_counts.items(), key=lambda item: (-item[1]["total"], item[0])):
        statuses = Counter(record.quality_status for record in market if record.symbol == symbol)
        symbol_rows.append({
            "symbol": symbol, "5m": counts["5m"], "15m": counts["15m"], "1h": counts["1h"],
            "4h": counts["4h"], "1d": counts["1d"], "csv": counts["csv"], "jsonl": counts["jsonl"],
            "total": counts["total"], "high_quality": statuses["HIGH"], "medium_quality": statuses["MEDIUM"],
            "low_quality": statuses["LOW"], "unusable": statuses["UNUSABLE"],
        })
    if symbol_rows:
        write_csv(output / "SYMBOL_FILE_MAP.csv", symbol_rows, list(symbol_rows[0]))

    raw_groups: dict[str, list[str]] = defaultdict(list)
    for record in records:
        raw_groups[record.raw_sha256].append(record.path)
    exact_duplicates = [paths for paths in raw_groups.values() if len(paths) > 1]

    grouped: dict[tuple[str, str], list[Record]] = defaultdict(list)
    for record in market:
        grouped[(record.symbol, record.timeframe)].append(record)
    coverage: list[dict[str, Any]] = []
    for (symbol, timeframe), items in sorted(grouped.items()):
        for index, left in enumerate(items):
            for right in items[index + 1:]:
                kind, seconds = relation(left, right)
                coverage.append({
                    "symbol": symbol, "timeframe": timeframe, "left_path": left.path,
                    "right_path": right.path, "relation": kind, "overlap_or_gap_seconds": seconds,
                })
    if coverage:
        write_csv(output / "COVERAGE_RELATIONSHIPS.csv", coverage, list(coverage[0]))

    issues = [record for record in market if record.quality_status in {"MEDIUM", "LOW", "UNUSABLE"}
              or record.twin_status not in {"NOT_APPLICABLE", "SEMANTICALLY_EQUIVALENT"}]
    quality_report = [
        "# Data Quality Report", "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", "",
        "## Corpus counts", "",
        table(["Measure", "Count"], [
            ("Repository files audited", len(records)), ("Market files parsed", len(market)),
            ("Unique market symbols", len(symbol_counts)), ("CSV/JSONL twin pairs", len(twins)),
            ("Exact raw duplicate groups", len(exact_duplicates)), ("Prior/background documents", len(documents)),
        ]), "", "## Market quality statuses", "", table(["Status", "Count"], sorted(quality.items())),
        "", "## Timeframe counts", "", table(["Timeframe", "Files"], sorted(timeframes.items())),
        "", "## Files requiring attention", "",
        table(["Path", "Quality", "Rows", "Gaps", "Duplicates", "Unclosed", "Twin", "Flags"], [
            (record.path, record.quality_status, record.actual_rows, record.gap_count,
             record.duplicate_timestamp_count, record.closed_false_count, record.twin_status, record.quality_flags)
            for record in issues[:400]
        ]) if issues else "No parsed market files require attention.",
        "", "## Interpretation constraints", "",
        "- `limitN` is nominal; `actual_rows` is authoritative.",
        "- CSV/JSONL twins count as one source only after semantic equivalence passes.",
        "- Missing fields remain unknown rather than neutral evidence.",
        "- Higher-timeframe rows become visible only after their own close time.",
        "- Data quality does not imply market direction.",
    ]
    (output / "DATA_QUALITY_REPORT.md").write_text("\n".join(quality_report), encoding="utf-8")

    duplicate_report = ["# Duplicate and Coverage Relationship Report", "", "## Exact raw-byte duplicates", ""]
    if exact_duplicates:
        for index, paths in enumerate(exact_duplicates, start=1):
            duplicate_report.append(f"### Group {index}")
            duplicate_report.extend(f"- `{path}`" for path in paths)
            duplicate_report.append("")
    else:
        duplicate_report.extend(["No exact raw-byte duplicate groups detected.", ""])
    duplicate_report.extend(["## CSV/JSONL twin status", "",
        table(["Stem", "Status", "CSV rows", "JSONL rows"], [
            (row["stem"], row["status"], row["csv_rows"], row["jsonl_rows"]) for row in twins
        ]) if twins else "No twin pairs detected.", "", "## Same-symbol/timeframe coverage", "",
        table(["Symbol", "TF", "Left", "Right", "Relation", "Seconds"], [
            (row["symbol"], row["timeframe"], row["left_path"], row["right_path"], row["relation"], row["overlap_or_gap_seconds"])
            for row in coverage[:700]
        ]) if coverage else "No comparable coverage pairs detected."])
    (output / "DUPLICATE_AND_OVERLAP_REPORT.md").write_text("\n".join(duplicate_report), encoding="utf-8")

    prior_rows = [{
        "path": record.path, "source_class": record.source_class, "linked_symbols": record.linked_symbols,
        "line_count": record.line_count, "encoding": record.parse_encoding,
        "extraction_status": record.extraction_status, "quality_flags": record.quality_flags,
    } for record in documents]
    if prior_rows:
        write_csv(output / "PRIOR_ANALYSIS_INDEX.csv", prior_rows, list(prior_rows[0]))
    (output / "PRIOR_ANALYSIS_INDEX.md").write_text("\n".join([
        "# Prior Analysis and Background Corpus Index", "",
        "These documents are hypothesis and audit sources, not ground-truth labels.", "",
        table(["Path", "Class", "Linked symbols", "Lines", "Encoding", "Extraction"], [
            (record.path, record.source_class, record.linked_symbols, record.line_count,
             record.parse_encoding, record.extraction_status) for record in documents
        ]) if documents else "No prior-analysis documents detected.",
    ]), encoding="utf-8")

    (output / "SYMBOL_FILE_MAP.md").write_text("\n".join([
        "# Symbol File Map", "", "CSV and JSONL are separate until equivalence is verified.", "",
        table(["Symbol", "5m", "15m", "1h", "4h", "1d", "CSV", "JSONL", "Total", "High", "Medium", "Low"], [
            (row["symbol"], row["5m"], row["15m"], row["1h"], row["4h"], row["1d"],
             row["csv"], row["jsonl"], row["total"], row["high_quality"], row["medium_quality"], row["low_quality"])
            for row in symbol_rows
        ]),
    ]), encoding="utf-8")

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository_files_audited": len(records),
        "source_class_counts": dict(sorted(classes.items())),
        "market_file_count": len(market),
        "unique_market_symbols": len(symbol_counts),
        "timeframe_counts": dict(sorted(timeframes.items())),
        "market_quality_counts": dict(sorted(quality.items())),
        "csv_jsonl_twin_counts": dict(sorted(Counter(row["status"] for row in twins).items())),
        "exact_raw_duplicate_groups": len(exact_duplicates),
        "coverage_relationship_counts": dict(sorted(Counter(row["relation"] for row in coverage).items())),
    }
    (output / "MANIFEST_SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("research/inventory/generated"))
    args = parser.parse_args(argv)
    print(json.dumps(build(args.root, args.output_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
