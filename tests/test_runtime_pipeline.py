#!/usr/bin/env python3
"""Clean-room tests for the Cognitive OS runtime-definition pipeline."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VOICE = ROOT / "pipelines" / "voice-to-sqlite.py"
REVIEW = ROOT / "pipelines" / "weekly-review.py"
BACKUP = ROOT / "pipelines" / "jsonl-backup.py"
SCHEMA = ROOT / "schemas" / "entry.schema.json"
SAMPLE = ROOT / "schemas" / "sample-entry.json"


class RuntimePipelineTests(unittest.TestCase):
    def run_script(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def sample_entry(self) -> dict:
        return json.loads(SAMPLE.read_text(encoding="utf-8"))

    def write_jsonl(self, path: Path, entries: list[dict]) -> None:
        path.write_text(
            "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in entries),
            encoding="utf-8",
        )

    def ingest_sample(self, directory: Path) -> tuple[Path, Path]:
        db = directory / "cognitive.db"
        jsonl = directory / "entries.jsonl"
        result = self.run_script(
            VOICE,
            "--db",
            str(db),
            "--jsonl",
            str(jsonl),
            "--input",
            str(SAMPLE),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return db, jsonl

    def test_sample_entry_is_accepted_by_backup_contract(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            jsonl = directory / "sample.jsonl"
            self.write_jsonl(jsonl, [self.sample_entry()])
            result = self.run_script(BACKUP, "--jsonl", str(jsonl), "--schema", str(SCHEMA))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("1 record(s)", result.stdout)

    def test_voice_pipeline_writes_identical_canonical_entry_to_sqlite_and_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            db, jsonl = self.ingest_sample(Path(raw_directory))
            archived = json.loads(jsonl.read_text(encoding="utf-8").splitlines()[0])
            with sqlite3.connect(db) as connection:
                stored_json = connection.execute(
                    "SELECT entry_json FROM entries WHERE id = ?", (archived["id"],)
                ).fetchone()[0]
            self.assertEqual(json.loads(stored_json), archived)

    def test_voice_pipeline_rejects_invalid_energy(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            result = self.run_script(
                VOICE,
                "--db",
                str(Path(raw_directory) / "cognitive.db"),
                "--text",
                "Energy was too high",
                "--energy",
                "11",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("energy must be between 1 and 10", result.stderr)

    def test_gemini_flash_is_explicit_and_fails_without_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            result = self.run_script(
                VOICE,
                "--db",
                str(Path(raw_directory) / "cognitive.db"),
                "--text",
                "A voice capture",
                "--categorizer",
                "gemini-flash",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("GEMINI_FLASH_ENDPOINT", result.stderr)

    def test_weekly_review_contains_ingested_entry_and_domain_summary(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            db, _ = self.ingest_sample(directory)
            output = directory / "2026-W35.md"
            result = self.run_script(
                REVIEW,
                "--db",
                str(db),
                "--output",
                str(output),
                "--week",
                "2026-W35",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = output.read_text(encoding="utf-8")
            self.assertIn("# Cognitive OS Weekly Review — 2026-W35", report)
            self.assertIn("| health | 1 | 8.0 | 0.70 |", report)
            self.assertIn("Walked after lunch", report)

    def test_backup_rejects_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            jsonl = Path(raw_directory) / "corrupt.jsonl"
            jsonl.write_text("{not valid json}\n", encoding="utf-8")
            result = self.run_script(BACKUP, "--jsonl", str(jsonl), "--schema", str(SCHEMA))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("malformed JSON", result.stderr)
            self.assertIn("line 1", result.stderr)

    def test_backup_rejects_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            jsonl = Path(raw_directory) / "duplicate.jsonl"
            entry = self.sample_entry()
            self.write_jsonl(jsonl, [entry, entry])
            result = self.run_script(BACKUP, "--jsonl", str(jsonl), "--schema", str(SCHEMA))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate entry id", result.stderr)


if __name__ == "__main__":
    unittest.main()
