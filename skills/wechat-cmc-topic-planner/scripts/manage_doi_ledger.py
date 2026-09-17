#!/usr/bin/env python3
"""Maintain a cross-report DOI ledger and check candidate DOI uniqueness."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote


DOI_RE = re.compile(r"(?i)(10\.\d{4,9}/[^\s<>\"']+)")
TITLE_ROW_RE = re.compile(
    r"^\|\s*(?:原始标题|候选标题)\s*\|\s*(.*?)\s*\|\s*$",
    re.IGNORECASE,
)
SOURCE_ROW_RE = re.compile(r"^\|\s*来源信息\s*\|\s*(.*?)\s*\|\s*$", re.IGNORECASE)
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
LEDGER_COLUMNS = ("doi", "first_seen_report", "first_seen_date", "original_title")


@dataclass(frozen=True)
class DoiRecord:
    doi: str
    report: str
    date: str
    title: str = ""


def discover_project_root() -> Path:
    candidates = [Path.cwd(), *Path.cwd().parents]
    candidates.extend(Path(__file__).resolve().parents)
    for candidate in candidates:
        if (candidate / "reports" / "topics").is_dir():
            return candidate
    raise FileNotFoundError(
        "Could not find reports/topics. Pass --project-root explicitly."
    )


def normalize_doi(value: str) -> str | None:
    text = html.unescape(unquote(value.strip()))
    text = re.sub(
        r"^https?://(?:dx\.)?doi\.org/",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"^doi:\s*", "", text, flags=re.IGNORECASE)
    match = DOI_RE.search(text)
    if not match:
        return None

    doi = match.group(1)
    doi = re.split(r"\]\(", doi, maxsplit=1)[0]
    while doi and doi[-1] in ".,;:，。；：]>}":
        doi = doi[:-1]
    if doi.endswith(")") and doi.count("(") < doi.count(")"):
        doi = doi[:-1]
    return doi.lower()


def extract_dois(value: str) -> list[str]:
    matches = DOI_RE.findall(html.unescape(unquote(value)))
    normalized: list[str] = []
    for match in matches:
        doi = normalize_doi(match)
        if doi and doi not in normalized:
            normalized.append(doi)
    return normalized


def clean_markdown_cell(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = value.replace("**", "").replace("`", "")
    return " ".join(value.split())


def report_sort_key(path: Path) -> tuple[str, str]:
    match = DATE_RE.search(path.name)
    return (match.group(1) if match else "9999-99-99", path.name)


def report_date(path: Path) -> str:
    match = DATE_RE.search(path.name)
    return match.group(1) if match else ""


def extract_from_source_rows(path: Path) -> list[DoiRecord]:
    current_title = ""
    records: list[DoiRecord] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        title_match = TITLE_ROW_RE.match(line)
        if title_match:
            current_title = clean_markdown_cell(title_match.group(1))
            continue

        source_match = SOURCE_ROW_RE.match(line)
        if not source_match:
            continue

        for doi in extract_dois(source_match.group(1)):
            records.append(
                DoiRecord(
                    doi=doi,
                    report=path.name,
                    date=report_date(path),
                    title=current_title,
                )
            )
    return records


def extract_from_all_text(path: Path) -> list[DoiRecord]:
    return [
        DoiRecord(
            doi=doi,
            report=path.name,
            date=report_date(path),
            title="",
        )
        for doi in extract_dois(path.read_text(encoding="utf-8-sig"))
    ]


def build_ledger(reports_dir: Path, scope: str) -> list[DoiRecord]:
    first_seen: dict[str, DoiRecord] = {}
    reports = sorted(reports_dir.glob("*.md"), key=report_sort_key)
    for report in reports:
        records = (
            extract_from_all_text(report)
            if scope == "all"
            else extract_from_source_rows(report)
        )
        for record in records:
            first_seen.setdefault(record.doi, record)
    return sorted(first_seen.values(), key=lambda item: (item.date, item.report, item.doi))


def write_ledger(path: Path, records: list[DoiRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["\t".join(LEDGER_COLUMNS)]
    for record in records:
        values = (
            record.doi,
            record.report,
            record.date,
            record.title.replace("\t", " ").replace("\n", " "),
        )
        lines.append("\t".join(values))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_ledger(path: Path) -> dict[str, DoiRecord]:
    if not path.is_file():
        return {}

    records: dict[str, DoiRecord] = {}
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if not lines:
        return records

    header = lines[0].split("\t")
    if tuple(header[: len(LEDGER_COLUMNS)]) != LEDGER_COLUMNS:
        raise ValueError(f"Unexpected ledger header in {path}")

    for line in lines[1:]:
        if not line.strip():
            continue
        values = line.split("\t")
        if len(values) < 3:
            continue
        doi, report, date = values[:3]
        title = values[3] if len(values) > 3 else ""
        records[doi.lower()] = DoiRecord(doi.lower(), report, date, title)
    return records


def load_input_dois(args: argparse.Namespace) -> list[str]:
    values = list(args.doi or [])
    if args.input_file:
        values.extend(args.input_file.read_text(encoding="utf-8-sig").splitlines())
    if not values and not sys.stdin.isatty():
        values.extend(sys.stdin.read().splitlines())

    normalized: list[str] = []
    invalid: list[str] = []
    for value in values:
        if not value.strip():
            continue
        doi = normalize_doi(value)
        if not doi:
            invalid.append(value)
        elif doi not in normalized:
            normalized.append(doi)
    if invalid:
        raise ValueError("Invalid DOI input: " + ", ".join(invalid))
    return normalized


def command_sync(args: argparse.Namespace) -> int:
    project_root = args.project_root
    reports_dir = args.reports_dir or project_root / "reports" / "topics"
    ledger_path = args.ledger or reports_dir / "doi-ledger.tsv"
    if not reports_dir.is_dir():
        raise FileNotFoundError(f"Reports directory not found: {reports_dir}")

    records = build_ledger(reports_dir, args.scope)
    previous = read_ledger(ledger_path)
    added = [record.doi for record in records if record.doi not in previous]
    if not args.dry_run:
        write_ledger(ledger_path, records)

    print(
        json.dumps(
            {
                "ledger": str(ledger_path),
                "reports_dir": str(reports_dir),
                "scope": args.scope,
                "reports_scanned": len(list(reports_dir.glob("*.md"))),
                "total_dois": len(records),
                "added_since_last_sync": added,
                "dry_run": args.dry_run,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def command_check(args: argparse.Namespace) -> int:
    project_root = args.project_root
    reports_dir = args.reports_dir or project_root / "reports" / "topics"
    ledger_path = args.ledger or reports_dir / "doi-ledger.tsv"
    ledger = read_ledger(ledger_path)
    dois = load_input_dois(args)

    allowed: list[str] = []
    blocked: list[dict[str, str]] = []
    for doi in dois:
        record = ledger.get(doi)
        if record:
            blocked.append(
                {
                    "doi": doi,
                    "status": "duplicate",
                    "first_seen_report": record.report,
                    "first_seen_date": record.date,
                    "original_title": record.title,
                }
            )
        else:
            allowed.append(doi)

    result = {
        "ledger": str(ledger_path),
        "checked": len(dois),
        "allowed": allowed,
        "blocked": blocked,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.fail_on_duplicate and blocked:
        return 1
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Maintain and check the cross-report DOI ledger."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("sync", "check"):
        command = subparsers.add_parser(name)
        command.add_argument(
            "--project-root",
            type=Path,
            default=None,
            help="Project root containing reports/topics.",
        )
        command.add_argument(
            "--reports-dir",
            type=Path,
            default=None,
            help="Directory containing topic reports. Defaults to reports/topics.",
        )
        command.add_argument(
            "--ledger",
            type=Path,
            default=None,
            help="Ledger path. Defaults to reports/topics/doi-ledger.tsv.",
        )

    sync = subparsers.choices["sync"]
    sync.add_argument(
        "--scope",
        choices=("source-rows", "all"),
        default="source-rows",
        help="Extract only decision-card source rows, or every DOI in every report.",
    )
    sync.add_argument("--dry-run", action="store_true")

    check = subparsers.choices["check"]
    check.add_argument("--doi", action="append", default=[])
    check.add_argument("--input-file", type=Path)
    check.add_argument("--fail-on-duplicate", action="store_true")

    args = parser.parse_args()
    if args.project_root is None:
        args.project_root = discover_project_root()
    args.project_root = args.project_root.resolve()
    if args.reports_dir:
        args.reports_dir = args.reports_dir.resolve()
    if args.ledger:
        args.ledger = args.ledger.resolve()
    if getattr(args, "input_file", None):
        args.input_file = args.input_file.resolve()
    return args


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    try:
        args = parse_args()
        if args.command == "sync":
            return command_sync(args)
        if args.command == "check":
            return command_check(args)
        raise AssertionError(args.command)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
