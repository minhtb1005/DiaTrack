"""Small persistent store for SOAP, nutrition and booking workflows."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

DB_PATH = Path(os.getenv("CARE_DB_PATH", "metadata/care_workflows.db"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def uid() -> str:
    return uuid4().hex


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS soap_notes(
          id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, transcript TEXT NOT NULL,
          subjective TEXT NOT NULL, objective TEXT NOT NULL, assessment TEXT NOT NULL,
          plan TEXT NOT NULL DEFAULT '', missing_json TEXT NOT NULL, evidence_json TEXT NOT NULL,
          status TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
          created_by TEXT NOT NULL, signed_by TEXT, created_at TEXT NOT NULL, signed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS soap_audit(
          id TEXT PRIMARY KEY, note_id TEXT NOT NULL, actor_id TEXT NOT NULL,
          action TEXT NOT NULL, before_json TEXT, after_json TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS nutrition_profiles(
          patient_id TEXT PRIMARY KEY, allergies_json TEXT NOT NULL,
          preferences_json TEXT NOT NULL, confirmed_no_allergies INTEGER NOT NULL DEFAULT 0,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS meal_plans(
          id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, scenario TEXT,
          meals_json TEXT NOT NULL, status TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
          created_by TEXT NOT NULL, reviewed_by TEXT, created_at TEXT NOT NULL, reviewed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS meal_logs(
          id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, plan_id TEXT,
          food_json TEXT NOT NULL, eaten_at TEXT NOT NULL, glucose_log_id INTEGER, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS bookings(
          id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, specialty TEXT NOT NULL,
          doctor_id TEXT NOT NULL, slot_date TEXT NOT NULL, slot_time TEXT NOT NULL,
          source TEXT NOT NULL, status TEXT NOT NULL, consent_reminder INTEGER NOT NULL DEFAULT 0,
          confidence REAL, needs_human INTEGER NOT NULL DEFAULT 0, parent_id TEXT,
          created_by TEXT NOT NULL, approved_by TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_booking_slot
          ON bookings(doctor_id,slot_date,slot_time)
          WHERE status IN ('held','patient_confirmed','approved');
        CREATE TABLE IF NOT EXISTS booking_audit(
          id TEXT PRIMARY KEY, booking_id TEXT NOT NULL, actor_id TEXT NOT NULL,
          action TEXT NOT NULL, detail_json TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS booking_reminders(
          id TEXT PRIMARY KEY, booking_id TEXT NOT NULL UNIQUE, patient_id TEXT NOT NULL,
          channel TEXT NOT NULL, sent_at TEXT NOT NULL
        );
        """)


def row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def load(value: str) -> Any:
    return json.loads(value)


init_db()
