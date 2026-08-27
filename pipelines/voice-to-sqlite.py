#!/usr/bin/env python3
"""VoxLog voice capture -> validated Cognitive OS entry -> SQLite/JSONL.

PSEUDOCODE
==========
1. Read a VoxLog transcript or a normalized JSON capture.
2. Preserve raw_text, source, source_ref, and the capture timestamp.
3. Extract domain/value/unit/notes/sentiment/energy.
   - Use Gemini Flash when explicitly configured by the caller.
   - Otherwise use the supplied fields and a deterministic local fallback.
4. Add a stable entry id and created_at timestamp.
5. Validate the complete entry against the Cognitive OS entry contract.
6. Append the exact canonical JSON object to JSONL, if requested.
7. Insert the same object into SQLite in a transaction.
8. Print the entry and fail loudly on validation, duplicate-id, or I/O errors.

The executable implementation below intentionally uses only Python's standard
library. A production Gemini adapter can provide GEMINI_FLASH_ENDPOINT and
GEMINI_FLASH_API_KEY; the endpoint is kept provider-agnostic so this repository
is not coupled to a backend or hosted app.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ALLOWED_SOURCES = {"voxlog", "telegram", "logseq", "manual", "import"}
ALLOWED_EXTRACTION_METHODS = {"gemini-flash", "local-fallback", "manual", "import"}
REQUIRED_FIELDS = {
    "domain",
    "value",
    "unit",
    "notes",
    "sentiment",
    "energy",
    "timestamp",
}
ALLOWED_FIELDS = REQUIRED_FIELDS | {
    "id",
    "source",
    "source_ref",
    "raw_text",
    "extraction_method",
    "created_at",
}


def now_iso() -> str:
    """Return a timezone-aware ISO 8601 timestamp."""

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_iso_datetime(value: str, field_name: str) -> None:
    """Validate an ISO 8601 date-time with an explicit timezone."""

    if not isinstance(value, str) or "T" not in value:
        raise ValueError(f"{field_name} must be an ISO 8601 date-time")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError(f"{field_name} is not a valid ISO 8601 date-time: {value}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include a timezone offset or Z")


def validate_entry(entry: dict[str, Any]) -> None:
    """Validate the entry contract without requiring third-party packages."""

    if not isinstance(entry, dict):
        raise ValueError("entry must be a JSON object")
    missing = REQUIRED_FIELDS - entry.keys()
    if missing:
        raise ValueError(f"missing required field(s): {', '.join(sorted(missing))}")
    unknown = set(entry) - ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"unknown field(s): {', '.join(sorted(unknown))}")

    if not isinstance(entry["domain"], str) or not entry["domain"].strip():
        raise ValueError("domain must be a non-empty string")
    if entry["unit"] is not None and (
        not isinstance(entry["unit"], str) or not entry["unit"].strip()
    ):
        raise ValueError("unit must be a non-empty string or null")
    if entry["notes"] is not None and not isinstance(entry["notes"], str):
        raise ValueError("notes must be a string or null")

    sentiment = entry["sentiment"]
    if sentiment is not None:
        if isinstance(sentiment, bool) or not isinstance(sentiment, (int, float)):
            raise ValueError("sentiment must be a number or null")
        if not -1 <= sentiment <= 1:
            raise ValueError("sentiment must be between -1 and 1")

    energy = entry["energy"]
    if energy is not None:
        if isinstance(energy, bool) or not isinstance(energy, int):
            raise ValueError("energy must be an integer or null")
        if not 1 <= energy <= 10:
            raise ValueError("energy must be between 1 and 10")

    parse_iso_datetime(entry["timestamp"], "timestamp")
    if "created_at" in entry:
        parse_iso_datetime(entry["created_at"], "created_at")
    if "id" in entry:
        try:
            uuid.UUID(str(entry["id"]))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError("id must be a UUID") from exc
    if "source" in entry and entry["source"] not in ALLOWED_SOURCES:
        raise ValueError(f"source must be one of: {', '.join(sorted(ALLOWED_SOURCES))}")
    if "extraction_method" in entry and entry["extraction_method"] not in ALLOWED_EXTRACTION_METHODS:
        raise ValueError(
            "extraction_method must be one of: "
            + ", ".join(sorted(ALLOWED_EXTRACTION_METHODS))
        )
    for nullable_text in ("source_ref", "raw_text"):
        if nullable_text in entry and entry[nullable_text] is not None and not isinstance(entry[nullable_text], str):
            raise ValueError(f"{nullable_text} must be a string or null")


def parse_value(value: str | None) -> Any:
    """Parse JSON values supplied on the command line, falling back to text."""

    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def read_capture(args: argparse.Namespace) -> dict[str, Any]:
    """Read a normalized VoxLog JSON capture or construct one from CLI fields."""

    capture: dict[str, Any] = {}
    if args.input:
        source = Path(args.input)
        with source.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        if not isinstance(loaded, dict):
            raise ValueError("--input must contain one JSON object")
        capture.update(loaded)
    if args.text is not None:
        capture["raw_text"] = args.text
    for name in (
        "domain",
        "unit",
        "notes",
        "timestamp",
        "source",
        "source_ref",
        "sentiment",
        "energy",
        "id",
    ):
        value = getattr(args, name)
        if value is not None:
            capture[name] = value
    if args.value is not None:
        capture["value"] = parse_value(args.value)
    return capture


def categorize_with_gemini_flash(raw_text: str) -> dict[str, Any]:
    """Call a provider-agnostic Gemini Flash JSON endpoint when configured.

    The endpoint should accept {"model": "gemini-flash", "input": "..."} and
    return a JSON object containing any of domain, value, unit, notes, sentiment,
    and energy. Keeping this adapter explicit prevents silent network calls.
    """

    endpoint = os.environ.get("GEMINI_FLASH_ENDPOINT")
    api_key = os.environ.get("GEMINI_FLASH_API_KEY")
    if not endpoint or not api_key:
        raise RuntimeError(
            "Gemini Flash requested but GEMINI_FLASH_ENDPOINT and "
            "GEMINI_FLASH_API_KEY are not configured"
        )
    payload = json.dumps({"model": "gemini-flash", "input": raw_text}).encode("utf-8")
    request = Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            decoded = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Gemini Flash categorization failed: {exc}") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError("Gemini Flash endpoint must return a JSON object")
    return decoded


def extract_entry(capture: dict[str, Any], categorizer: str) -> dict[str, Any]:
    """Create a canonical entry from capture data and optional categorization."""

    raw_text = capture.get("raw_text")
    if raw_text is not None and not isinstance(raw_text, str):
        raise ValueError("raw_text must be a string")
    extracted: dict[str, Any] = {}
    method = "manual" if categorizer == "manual" else "local-fallback"
    if categorizer == "gemini-flash":
        if not raw_text:
            raise ValueError("Gemini Flash categorization requires raw_text")
        extracted = categorize_with_gemini_flash(raw_text)
        method = "gemini-flash"

    merged = dict(capture)
    merged.update({key: value for key, value in extracted.items() if value is not None})
    if "raw_text" not in merged:
        merged["raw_text"] = None
    if "domain" not in merged:
        merged["domain"] = "uncategorized"
    if "value" not in merged:
        merged["value"] = raw_text if raw_text is not None else ""
    if "unit" not in merged:
        merged["unit"] = None
    if "notes" not in merged:
        merged["notes"] = raw_text
    if "sentiment" not in merged:
        merged["sentiment"] = None
    if "energy" not in merged:
        merged["energy"] = None
    if "timestamp" not in merged:
        merged["timestamp"] = now_iso()
    merged.setdefault("id", str(uuid.uuid4()))
    merged.setdefault("source", "voxlog")
    merged.setdefault("source_ref", None)
    merged.setdefault("extraction_method", method)
    merged.setdefault("created_at", now_iso())

    entry = {key: merged[key] for key in ALLOWED_FIELDS if key in merged}
    validate_entry(entry)
    return entry


def canonical_json(entry: dict[str, Any]) -> str:
    return json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS entries (
            id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            value_json TEXT NOT NULL,
            unit TEXT,
            notes TEXT,
            sentiment REAL,
            energy INTEGER,
            timestamp TEXT NOT NULL,
            source TEXT,
            source_ref TEXT,
            raw_text TEXT,
            extraction_method TEXT,
            created_at TEXT NOT NULL,
            entry_json TEXT NOT NULL
        )
        """
    )
    connection.commit()


def append_jsonl(path: Path, serialized: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        handle.seek(0, os.SEEK_END)
        offset = handle.tell()
        handle.write(serialized + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return offset


def write_entry(entry: dict[str, Any], db_path: Path, jsonl_path: Path | None) -> None:
    serialized = canonical_json(entry)
    jsonl_offset: int | None = None
    if jsonl_path:
        jsonl_offset = append_jsonl(jsonl_path, serialized)
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path) as connection:
            initialize_database(connection)
            connection.execute(
                """
                INSERT INTO entries (
                    id, domain, value_json, unit, notes, sentiment, energy,
                    timestamp, source, source_ref, raw_text, extraction_method,
                    created_at, entry_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["id"],
                    entry["domain"],
                    json.dumps(entry["value"], ensure_ascii=False),
                    entry["unit"],
                    entry["notes"],
                    entry["sentiment"],
                    entry["energy"],
                    entry["timestamp"],
                    entry.get("source"),
                    entry.get("source_ref"),
                    entry.get("raw_text"),
                    entry.get("extraction_method"),
                    entry["created_at"],
                    serialized,
                ),
            )
    except Exception:
        if jsonl_path is not None and jsonl_offset is not None:
            with jsonl_path.open("r+b") as handle:
                handle.truncate(jsonl_offset)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="SQLite database path")
    parser.add_argument("--jsonl", help="Optional JSONL backup path")
    parser.add_argument("--input", help="JSON file containing one normalized capture object")
    parser.add_argument("--text", help="VoxLog transcript or other raw capture text")
    parser.add_argument("--domain")
    parser.add_argument("--value", help="JSON value, or plain text when not valid JSON")
    parser.add_argument("--unit")
    parser.add_argument("--notes")
    parser.add_argument("--sentiment", type=float)
    parser.add_argument("--energy", type=int)
    parser.add_argument("--timestamp")
    parser.add_argument("--source", choices=sorted(ALLOWED_SOURCES))
    parser.add_argument("--source-ref")
    parser.add_argument("--id")
    parser.add_argument(
        "--categorizer",
        choices=["local-fallback", "gemini-flash", "manual"],
        default="local-fallback",
        help="Extraction mode; local-fallback performs no network call",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.input and args.text is None:
        build_parser().error("provide --input or --text")
    try:
        capture = read_capture(args)
        entry = extract_entry(capture, args.categorizer)
        write_entry(entry, Path(args.db), Path(args.jsonl) if args.jsonl else None)
    except (OSError, sqlite3.Error, RuntimeError, ValueError) as exc:
        print(f"voice-to-sqlite: error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(entry, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
