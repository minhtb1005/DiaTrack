"""Read a triage case directly from the isolated SQLite store."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    test_root = (root / "test-results" / "triage-e2e").resolve()
    run_dir = Path(sys.argv[1]).resolve()
    if run_dir == test_root or test_root not in run_dir.parents:
        raise SystemExit("Invalid test database directory")
    with sqlite3.connect(run_dir / "auth.db") as conn:
        conn.row_factory = sqlite3.Row
        case = conn.execute("SELECT * FROM triage_reviews WHERE id=?", (sys.argv[2],)).fetchone()
        audit = conn.execute("SELECT * FROM triage_review_audit WHERE case_id=?", (sys.argv[2],)).fetchall()
        reviewer = conn.execute("SELECT id,role,is_verified FROM users WHERE username='triage_nurse'").fetchone()
    print(json.dumps({"case": dict(case) if case else None,
                      "audit": [dict(row) for row in audit],
                      "reviewer": dict(reviewer) if reviewer else None}, ensure_ascii=True))


if __name__ == "__main__":
    main()
