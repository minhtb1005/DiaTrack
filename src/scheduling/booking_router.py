from __future__ import annotations

import sqlite3
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
    suggestions = match_doctors(specialty_code=code, days_ahead=7, per_doctor=3)
    return {"emergency": False, "specialty_code": code, "specialty": SPECIALTY_MAP[code], "confidence": confidence, "needs_human": confidence < 0.6, "source": SOURCE, "suggestions": suggestions}


@router.post("/hold")
def hold(payload: HoldIn, user=Depends(require_role("user"))):
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
        alternatives = suggest(SuggestIn(need=payload.specialty), user)["suggestions"]
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
    with connect() as c:
        items = c.execute("SELECT * FROM bookings WHERE status='approved' AND consent_reminder=1").fetchall()
        for item in items:
            try:
                c.execute("INSERT INTO booking_reminders VALUES(?,?,?,?,?)", (uid(), item["id"], item["patient_id"], "in_app", now()))
                sent += 1
            except sqlite3.IntegrityError:
                pass
    return {"sent": sent, "channel": "in_app"}


@router.get("/coordination/dashboard")
def dashboard(user=Depends(require_role("receptionist", "admin"))):
    with connect() as c:
        counts = {r["status"]: r["n"] for r in c.execute("SELECT status,COUNT(*) n FROM bookings GROUP BY status")}
        approved = c.execute("SELECT COUNT(*) FROM bookings WHERE status='approved'").fetchone()[0]
        sourced = c.execute("SELECT COUNT(*) FROM bookings WHERE status='approved' AND source=?", (SOURCE,)).fetchone()[0]
        human = [dict(r) for r in c.execute("SELECT id,specialty,doctor_id,slot_date,slot_time,status FROM bookings WHERE needs_human=1 ORDER BY created_at")]
        pending = [dict(r) for r in c.execute("SELECT id,specialty,doctor_id,slot_date,slot_time,status FROM bookings WHERE status='patient_confirmed' ORDER BY created_at")]
    return {"workload": counts, "approved_count": approved, "sourced_specialty_rate": sourced / approved if approved else None, "needs_human": human, "pending": pending, "source": SOURCE}
