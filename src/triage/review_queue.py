"""Durable triage review queue. Patient output is withheld until a nurse decides."""
from __future__ import annotations

import sqlite3
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path

from src.auth import db as auth_db


def _conn() -> sqlite3.Connection:
    conn = auth_db._get_conn()
    conn.execute("""CREATE TABLE IF NOT EXISTS triage_reviews (
        id TEXT PRIMARY KEY, requester_id TEXT NOT NULL, message TEXT NOT NULL,
        latest_glucose_mgdl REAL, symptom_onset TEXT, proposed_priority TEXT NOT NULL,
        rationale TEXT NOT NULL, source TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending'
            CHECK(status IN ('pending','approved','revised','rejected')),
        final_priority TEXT, final_message TEXT, reviewer_id TEXT, reviewer_notes TEXT,
        created_at TEXT NOT NULL, reviewed_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS triage_review_audit (
        id TEXT PRIMARY KEY, case_id TEXT NOT NULL, actor_id TEXT NOT NULL,
        action TEXT NOT NULL, previous_priority TEXT, final_priority TEXT,
        notes TEXT, created_at TEXT NOT NULL, previous_message TEXT, final_message TEXT
    )""")
    columns = {row[1] for row in conn.execute("PRAGMA table_info(triage_review_audit)")}
    for column in ("previous_message", "final_message"):
        if column not in columns:
            conn.execute(f"ALTER TABLE triage_review_audit ADD COLUMN {column} TEXT")
    conn.commit()
    return conn


def create_case(requester_id: str, message: str, glucose: float | None, onset: str | None, proposal: dict) -> str:
    case_id = str(uuid.uuid4())
    conn = _conn()
    try:
        conn.execute("""INSERT INTO triage_reviews
            (id,requester_id,message,latest_glucose_mgdl,symptom_onset,proposed_priority,rationale,source,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)""", (case_id, requester_id, message, glucose, onset,
            proposal["proposed_priority"], proposal["rationale"], proposal["source"],
            datetime.now(timezone.utc).isoformat()))
        conn.commit()
        return case_id
    finally:
        conn.close()


def list_pending() -> list[dict]:
    conn = _conn()
    try:
        return [dict(row) for row in conn.execute("SELECT * FROM triage_reviews WHERE status='pending' ORDER BY created_at ASC LIMIT 100")]
    finally:
        conn.close()


def get_case(case_id: str) -> dict | None:
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM triage_reviews WHERE id=?", (case_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def handoff_for(case_id: str) -> dict | None:
    case = get_case(case_id)
    if case is None:
        return None
    return {
        "case_id": case["id"],
        "symptoms": case["message"],
        "latest_glucose_mgdl": case["latest_glucose_mgdl"],
        "symptom_onset": case["symptom_onset"],
        "missing_information": [
            label for value, label in (
                (case["latest_glucose_mgdl"], "Số đo đường huyết gần nhất"),
                (case["symptom_onset"], "Thời điểm bắt đầu triệu chứng"),
            ) if value is None or (isinstance(value, str) and not value.strip())
        ],
        "proposed_priority": case["proposed_priority"],
        "rationale": case["rationale"],
        "sources": [
            {"label": source.strip(), "href": "https://github.com/minhtb1005/DiaTrack/blob/main/docs/project_requirements.json"}
            for source in case["source"].split(";") if source.strip()
        ],
        "created_at": case["created_at"],
        "notice": "Phiếu bàn giao không phải chẩn đoán; quyết định xử trí do nhân viên y tế duyệt.",
    }


def decide(case_id: str, reviewer_id: str, decision: str, priority: str | None, message: str | None, notes: str | None) -> dict | None:
    conn = _conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM triage_reviews WHERE id=? AND status='pending'", (case_id,)).fetchone()
        if not row:
            conn.rollback()
            return None
        old = dict(row)
        final_priority = None if decision == "rejected" else (priority or old["proposed_priority"])
        final_message = message if decision != "rejected" else "Nhân viên y tế chưa duyệt đề xuất phân luồng. Vui lòng liên hệ cơ sở y tế."
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("""UPDATE triage_reviews SET status=?,final_priority=?,final_message=?,reviewer_id=?,reviewer_notes=?,reviewed_at=? WHERE id=?""",
            (decision, final_priority, final_message, reviewer_id, notes, now, case_id))
        conn.execute("""INSERT INTO triage_review_audit
            (id,case_id,actor_id,action,previous_priority,final_priority,notes,created_at,previous_message,final_message)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4()), case_id, reviewer_id, decision, old["proposed_priority"], final_priority,
             notes, now, old["message"], final_message))
        conn.commit()
        return get_case(case_id)
    finally:
        conn.close()


def audit_for(case_id: str) -> list[dict]:
    conn = _conn()
    try:
        return [dict(row) for row in conn.execute("SELECT * FROM triage_review_audit WHERE case_id=? ORDER BY created_at", (case_id,))]
    finally:
        conn.close()


def audit_report() -> dict:
    """Return de-identified reviewer disagreement and a separate red-flag gold check."""
    conn = _conn()
    try:
        rows = conn.execute("""SELECT previous_priority, final_priority
            FROM triage_review_audit WHERE action IN ('approved','revised')""").fetchall()
    finally:
        conn.close()
    reviewed = len(rows)
    disagreements = sum(row[0] != row[1] for row in rows)

    gold_path = Path(__file__).resolve().parents[2] / "data" / "evaluation" / "bench_triage.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    red_flags = [item for item in gold if item.get("kind") == "redflag"]
    from src.triage.red_flag import check_red_flag
    failures = []
    for item in red_flags:
        actual = check_red_flag(item["text"])
        if bool(actual.get("emergency")) != item["expect_emergency"] or actual.get("red_flag_type") != item.get("expect_group"):
            failures.append(item["id"])
    return {
        "reviewed_cases": reviewed,
        "disagreement_count": disagreements,
        "disagreement_rate": disagreements / reviewed if reviewed else None,
        "gold": {
            "dataset": "data/evaluation/bench_triage.json",
            "version": max((item.get("version", 0) for item in gold), default=0),
            "red_flag_cases": len(red_flags),
            "red_flag_failures": failures,
        },
    }
