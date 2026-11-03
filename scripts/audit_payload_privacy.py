"""Read-only SQLite privacy inventory. Reports no source values or filenames."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.shared.privacy import POLICY_VERSION, PrivacyError, redact_text


def scan_database(path: Path, provenance: str) -> dict:
    """Explicitly selected database only; no fallback, writes, or embedding calls."""
    report = {"id": hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:16], "provenance": provenance, "policy": POLICY_VERSION, "status": "scanned_rules_only", "rows": 0, "findings": []}
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        conn.execute("PRAGMA query_only=ON")
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
        for (table,) in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            for number, row in enumerate(conn.execute(f"SELECT * FROM {quoted}")):
                report["rows"] += 1
                counts = Counter()
                for value in row:
                    if isinstance(value, str):
                        try:
                            redact_text(value, counts)
                        except PrivacyError:
                            counts["requires_review"] += 1
                    elif isinstance(value, bytes):
                        counts["uninspected_blob"] += 1
                counts = +counts
                if counts:
                    record_id = hashlib.sha256(f"{table}:{number}".encode()).hexdigest()[:16]
                    report["findings"].append({"id": record_id, "counts": dict(counts)})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("databases", type=Path, nargs="+")
    parser.add_argument("--provenance", choices=["public_guideline", "synthetic", "user", "unknown"], required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if not all(p.is_file() for p in args.databases):
        parser.error("all explicitly selected databases must exist")
    if args.report.resolve() in [p.resolve() for p in args.databases]:
        parser.error("report cannot overwrite a source")
    reports = []
    for path in args.databases:
        try:
            reports.append(scan_database(path, args.provenance))
        except sqlite3.Error:
            reports.append({"id": hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:16], "status": "scan_failed"})
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    return int(any(r["status"] == "scan_failed" for r in reports))


if __name__ == "__main__":
    raise SystemExit(main())
