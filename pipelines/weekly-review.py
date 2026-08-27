#!/usr/bin/env python3
"""Generate a deterministic weekly markdown review from Cognitive OS SQLite.

The report is a derived review artifact. It never edits source entries. The
week is identified by ISO week (for example, 2026-W34) and timestamps are
parsed with their timezone information before comparison.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def iso_week_bounds(week: str) -> tuple[date, date]:
    try:
        year_text, week_text = week.upper().split("-W", 1)
        year = int(year_text)
        week_number = int(week_text)
        start = date.fromisocalendar(year, week_number, 1)
    except (ValueError, IndexError) as exc:
        raise ValueError("week must use ISO format YYYY-Www, for example 2026-W34") from exc
    return start, start + timedelta(days=7)


def parse_timestamp(value: str) -> datetime:
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp has no timezone: {value}")
    return parsed


def display_value(value_json: str, unit: str | None) -> str:
    try:
        value: Any = json.loads(value_json)
    except json.JSONDecodeError:
        value = value_json
    if isinstance(value, (dict, list)):
        rendered = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        rendered = str(value)
    return f"{rendered} {unit}" if unit else rendered


def md_cell(value: Any) -> str:
    return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")


def fetch_entries(db_path: Path, start: date, end: date) -> list[sqlite3.Row]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                """
                SELECT id, domain, value_json, unit, notes, sentiment, energy,
                       timestamp, source
                FROM entries
                ORDER BY timestamp ASC, id ASC
                """
            ).fetchall()
        except sqlite3.Error as exc:
            raise RuntimeError(f"could not read entries table: {exc}") from exc
    selected: list[sqlite3.Row] = []
    for row in rows:
        timestamp = parse_timestamp(row["timestamp"])
        timestamp_utc = timestamp.astimezone(timezone.utc)
        if start <= timestamp_utc.date() < end:
            selected.append(row)
    return selected


def render_report(rows: list[sqlite3.Row], week: str, start: date, end: date) -> str:
    by_domain: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        by_domain[row["domain"]].append(row)

    lines = [
        f"# Cognitive OS Weekly Review — {week}",
        "",
        f"**Window:** {start.isoformat()} through {(end - timedelta(days=1)).isoformat()} (UTC date boundary)",
        f"**Entries:** {len(rows)}",
        "",
        "> This is a derived review artifact. Source entries remain in SQLite and their JSONL/Git archive.",
        "",
    ]
    if not rows:
        lines.extend([
            "## Summary",
            "",
            "No entries were recorded for this ISO week.",
            "",
            "## Questions for next week",
            "",
            "- What should be captured more consistently?",
            "",
        ])
        return "\n".join(lines)

    lines.extend(["## Domain summary", "", "| Domain | Entries | Average energy | Average sentiment |", "| --- | ---: | ---: | ---: |"])
    for domain in sorted(by_domain):
        domain_rows = by_domain[domain]
        energies = [row["energy"] for row in domain_rows if row["energy"] is not None]
        sentiments = [row["sentiment"] for row in domain_rows if row["sentiment"] is not None]
        avg_energy = f"{sum(energies) / len(energies):.1f}" if energies else "—"
        avg_sentiment = f"{sum(sentiments) / len(sentiments):.2f}" if sentiments else "—"
        lines.append(f"| {md_cell(domain)} | {len(domain_rows)} | {avg_energy} | {avg_sentiment} |")

    lines.extend(["", "## Entries", ""])
    for domain in sorted(by_domain):
        lines.extend([f"### {domain}", "", "| Timestamp | Value | Sentiment | Energy | Source | Notes |", "| --- | --- | ---: | ---: | --- | --- |"])
        for row in by_domain[domain]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        md_cell(row["timestamp"]),
                        md_cell(display_value(row["value_json"], row["unit"])),
                        md_cell(row["sentiment"]),
                        md_cell(row["energy"]),
                        md_cell(row["source"]),
                        md_cell(row["notes"]),
                    ]
                )
                + " |"
            )
        lines.append("")

    lines.extend([
        "## Human review",
        "",
        "- What pattern is worth continuing?",
        "- What needs a new capture habit or a domain-specific field?",
        "- What decision should become a new life entry?",
        "",
    ])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="SQLite database path")
    parser.add_argument("--output", required=True, help="Markdown report path")
    parser.add_argument(
        "--week",
        default=date.today().strftime("%G-W%V"),
        help="ISO week to review, e.g. 2026-W34 (default: current week)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        start, end = iso_week_bounds(args.week)
        rows = fetch_entries(Path(args.db), start, end)
        report = render_report(rows, args.week.upper(), start, end)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report + "\n", encoding="utf-8")
    except (OSError, sqlite3.Error, RuntimeError, ValueError) as exc:
        print(f"weekly-review: error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {len(rows)} entries to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
