#!/usr/bin/env python3
"""Validate a Cognitive OS JSONL backup for corruption and duplicate IDs.

The validator treats every physical line as a record. Blank lines, malformed
JSON, missing required fields, invalid field values, and duplicate IDs are
reported with their line numbers. A non-zero exit status means the backup is
not safe to use for recovery.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable


REQUIRED_FIELDS = {
    "domain",
    "value",
    "unit",
    "notes",
    "sentiment",
    "energy",
    "timestamp",
}


def load_entry_validator() -> tuple[Callable[[dict[str, Any]], None], set[str]]:
    """Reuse the reference entry validator without requiring a package install."""

    script = Path(__file__).with_name("voice-to-sqlite.py")
    spec = importlib.util.spec_from_file_location("cognitive_os_voice_pipeline", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load validator from {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_entry, set(module.ALLOWED_FIELDS)


def load_schema_requirements(schema_path: Path) -> set[str]:
    with schema_path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    if not isinstance(schema, dict) or not isinstance(schema.get("required"), list):
        raise ValueError("schema must contain a required array")
    required = set(schema["required"])
    if not REQUIRED_FIELDS.issubset(required):
        raise ValueError("schema required fields do not include the Cognitive OS entry contract")
    return required


def validate_jsonl(jsonl_path: Path, schema_path: Path) -> tuple[int, list[str]]:
    validate_entry, allowed_fields = load_entry_validator()
    schema_required = load_schema_requirements(schema_path)
    errors: list[str] = []
    seen_ids: set[str] = set()
    records = 0

    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                errors.append(f"line {line_number}: blank line is not a JSONL record")
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_number}: malformed JSON ({exc.msg} at column {exc.colno})")
                continue
            records += 1
            if not isinstance(record, dict):
                errors.append(f"line {line_number}: record must be a JSON object")
                continue
            missing_from_schema = schema_required - record.keys()
            if missing_from_schema:
                errors.append(
                    f"line {line_number}: missing schema field(s): "
                    + ", ".join(sorted(missing_from_schema))
                )
            try:
                validate_entry(record)
            except ValueError as exc:
                errors.append(f"line {line_number}: {exc}")
            if set(record) - allowed_fields:
                errors.append(
                    f"line {line_number}: unknown field(s): "
                    + ", ".join(sorted(set(record) - allowed_fields))
                )
            entry_id = record.get("id")
            if entry_id is not None:
                if entry_id in seen_ids:
                    errors.append(f"line {line_number}: duplicate entry id: {entry_id}")
                seen_ids.add(entry_id)

    return records, errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", required=True, help="JSONL backup path")
    parser.add_argument(
        "--schema",
        default=str(Path(__file__).parents[1] / "schemas" / "entry.schema.json"),
        help="Entry schema path",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        records, errors = validate_jsonl(Path(args.jsonl), Path(args.schema))
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"jsonl-backup: error: {exc}", file=sys.stderr)
        return 1
    if errors:
        print(f"JSONL invalid: {len(errors)} issue(s) across {records} parsed record(s)", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"JSONL valid: {records} record(s), {records} unique/validated record(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
