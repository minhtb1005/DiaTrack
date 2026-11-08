from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.auth.dependencies import get_current_user, require_role
from src.care_store import connect, dump, now, row, uid
from src.scheduling.slot_generator import SPECIALTY_MAP, match_doctors

router = APIRouter(prefix="/v1/bookings", tags=["bookings"])
SOURCE = "docs/project_requirements.json#projects.258-booking"
EMERGENCY = ("đau ngực", "méo miệng", "lơ mơ", "chảy mủ", "hoại tử", "thở nhanh", "nôn")


class SuggestIn(BaseModel):
    need: str = Field(min_length=1, max_length=2000)


class HoldIn(BaseModel):
    specialty: str
    doctor_id: str
    slot_date: str
    slot_time: str
    source: str = SOURCE
    consent_reminder: bool = False
    confidence: float | None = Field(None, ge=0, le=1)
    parent_id: str | None = None


def _booking(booking_id: str) -> dict[str, Any] | None:
    with connect() as c:
        return row(c.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone())


def _can_read(item: dict[str, Any], user: dict[str, Any]) -> None:
    if user["role"] == "user" and item["patient_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")


def _clock() -> datetime:
    override = os.getenv("BOOKING_REMINDER_NOW")
    return datetime.fromisoformat(override) if override else datetime.now(timezone.utc)


def _available_suggestions(specialty_code: str) -> list[dict[str, Any]]:
    suggestions = match_doctors(specialty_code=specialty_code, days_ahead=7, per_doctor=200)
    with connect() as c:
        occupied = {(x["doctor_id"], x["slot_date"], x["slot_time"]) for x in c.execute("SELECT doctor_id,slot_date,slot_time FROM bookings WHERE status IN ('held','patient_confirmed','approved')")}
    for doctor in suggestions:
        doctor["slots"] = [x for x in doctor["slots"] if (doctor["doctor_id"], x["date"], x["time"]) not in occupied][:3]
    return [doctor for doctor in suggestions if doctor["slots"]]


@router.post("/suggest")
def suggest(payload: SuggestIn, user=Depends(get_current_user)):
    text = payload.need.casefold()
    if any(x in text for x in EMERGENCY):
        return {"emergency": True, "message": "Có dấu hiệu cảnh báo: gọi 115 hoặc đến cơ sở y tế ngay.", "suggestions": []}
    if any(x in text for x in ("mắt", "võng mạc", "thận", "chân", "biến chứng")):
        code, confidence = "Endocrinology_Complication", 0.9
    elif any(x in text for x in ("ăn", "dinh dưỡng", "thực đơn")):
        code, confidence = "Nutrition_Lifestyle", 0.9
    elif any(x in text for x in ("đái tháo đường", "tiểu đường", "nội tiết")):
        code, confidence = "Endocrinology_General", 0.9
    else:
        code, confidence = "Endocrinology_General", 0.4
    suggestions = _available_suggestions(code)
    return {"emergency": False, "specialty_code": code, "specialty": SPECIALTY_MAP[code], "confidence": confidence, "needs_human": confidence < 0.6, "source": SOURCE, "suggestions": suggestions}


@router.get("/roster")
def roster(specialty: str, user=Depends(get_current_user)):
    if specialty not in SPECIALTY_MAP:
        raise HTTPException(422, "Unknown specialty")
    return {"specialty_code": specialty, "specialty": SPECIALTY_MAP[specialty], "source": SOURCE, "doctors": _available_suggestions(specialty)}


@router.post("/hold")
def hold(payload: HoldIn, user=Depends(require_role("user"))):
    if payload.parent_id:
        parent = _booking(payload.parent_id)
        if not parent or parent["patient_id"] != user["id"]:
            raise HTTPException(404, "Booking to reschedule not found")
        if parent["status"] != "approved":
            raise HTTPException(409, "Only an approved booking can be rescheduled")
    doctors = {d["doctor_id"]: d for d in match_doctors(specialty_code=payload.specialty, days_ahead=14, per_doctor=200, max_doctors=20)}
    doctor = doctors.get(payload.doctor_id)
    if not doctor or not any(s["date"] == payload.slot_date and s["time"] == payload.slot_time for s in doctor["slots"]):
        raise HTTPException(422, "Slot is not in the current sourced roster")
    booking_id, created = uid(), now()
    try:
        with connect() as c:
            c.execute("INSERT INTO bookings VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                booking_id, user["id"], payload.specialty, payload.doctor_id, payload.slot_date, payload.slot_time,
                payload.source, "held", int(payload.consent_reminder), payload.confidence,
                int(payload.confidence is not None and payload.confidence < 0.6), payload.parent_id,
                user["id"], None, created, created,
            ))
            c.execute("INSERT INTO booking_audit VALUES(?,?,?,?,?,?)", (uid(), booking_id, user["id"], "held", dump(payload.model_dump()), created))
    except sqlite3.IntegrityError:
        alternatives = _available_suggestions(payload.specialty)
        raise HTTPException(409, detail={"message": "Slot is no longer available", "alternatives": alternatives})
    return _booking(booking_id)


@router.post("/{booking_id}/confirm")
def confirm(booking_id: str, user=Depends(require_role("user"))):
    item = _booking(booking_id)
    if not item or item["patient_id"] != user["id"]:
        raise HTTPException(404, "Booking not found")
    if item["status"] != "held":
        raise HTTPException(409, "Booking cannot be confirmed")
    with connect() as c:
        c.execute("UPDATE bookings SET status='patient_confirmed',updated_at=? WHERE id=?", (now(), booking_id))
        c.execute("INSERT INTO booking_audit VALUES(?,?,?,?,?,?)", (uid(), booking_id, user["id"], "patient_confirmed", "{}", now()))
    return _booking(booking_id)


@router.post("/{booking_id}/approve")
def approve(booking_id: str, user=Depends(require_role("receptionist", "admin"))):
    item = _booking(booking_id)
    if not item:
        raise HTTPException(404, "Booking not found")
    if item["status"] != "patient_confirmed":
        raise HTTPException(409, "Patient confirmation required")
    updated = now()
    with connect() as c:
        if item["parent_id"]:
            c.execute("UPDATE bookings SET status='rescheduled',updated_at=? WHERE id=? AND status='approved'", (updated, item["parent_id"]))
        c.execute("UPDATE bookings SET status='approved',approved_by=?,updated_at=? WHERE id=?", (user["id"], updated, booking_id))
        c.execute("INSERT INTO booking_audit VALUES(?,?,?,?,?,?)", (uid(), booking_id, user["id"], "approved", dump({"parent_id": item["parent_id"]}), updated))
    return _booking(booking_id)


@router.get("/{booking_id}")
def get_booking(booking_id: str, user=Depends(get_current_user)):
    item = _booking(booking_id)
    if not item:
        raise HTTPException(404, "Booking not found")
    _can_read(item, user)
    return item


@router.post("/reminders/run")
def run_reminders(user=Depends(require_role("receptionist", "admin"))):
    sent = 0
    current = _clock()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    deadline = current + timedelta(hours=24)
    with connect() as c:
        items = c.execute("SELECT * FROM bookings WHERE status='approved' AND consent_reminder=1").fetchall()
        for item in items:
            appointment = datetime.fromisoformat(f"{item['slot_date']}T{item['slot_time']}:00+07:00")
            if not current < appointment <= deadline:
                continue
            try:
                c.execute("INSERT INTO booking_reminders VALUES(?,?,?,?,?)", (uid(), item["id"], item["patient_id"], "in_app", now()))
                sent += 1
            except sqlite3.IntegrityError:
                pass
    return {"sent": sent, "channel": "in_app"}


@router.post("/{booking_id}/human-review")
def resolve_human_review(booking_id: str, user=Depends(require_role("receptionist", "admin"))):
    item = _booking(booking_id)
    if not item:
        raise HTTPException(404, "Booking not found")
    if not item["needs_human"]:
        raise HTTPException(409, "Booking does not require human review")
    reviewed = now()
    with connect() as c:
        c.execute("UPDATE bookings SET needs_human=0,updated_at=? WHERE id=?", (reviewed, booking_id))
        c.execute("INSERT INTO booking_audit VALUES(?,?,?,?,?,?)", (uid(), booking_id, user["id"], "human_reviewed", "{}", reviewed))
    return {"id": booking_id, "needs_human": False, "reviewed_at": reviewed}


@router.get("/coordination/dashboard")
def dashboard(user=Depends(require_role("receptionist", "admin"))):
    with connect() as c:
        counts = {r["status"]: r["n"] for r in c.execute("SELECT status,COUNT(*) n FROM bookings GROUP BY status")}
        approved = c.execute("SELECT COUNT(*) FROM bookings WHERE status='approved'").fetchone()[0]
        sourced = c.execute("SELECT COUNT(*) FROM bookings WHERE status='approved' AND source=?", (SOURCE,)).fetchone()[0]
        human = [dict(r) for r in c.execute("SELECT id,specialty,doctor_id,slot_date,slot_time,status FROM bookings WHERE needs_human=1 ORDER BY created_at")]
        pending = [dict(r) for r in c.execute("SELECT id,specialty,doctor_id,slot_date,slot_time,status FROM bookings WHERE status='patient_confirmed' ORDER BY created_at")]
    return {"workload": counts, "approved_count": approved, "sourced_specialty_rate": sourced / approved if approved else None, "needs_human": human, "pending": pending, "source": SOURCE}
