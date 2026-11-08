from __future__ import annotations

import html
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from src.auth.dependencies import get_current_user, require_role
from src.care_store import connect, dump, load, now, row, uid
from src.diabetes.glucose_tracker import get_logs

router = APIRouter(prefix="/v1/soap", tags=["soap-workflow"])
ICD_SOURCE = "https://icd.who.int/browse10/2019/en#/E11"


class DraftIn(BaseModel):
    patient_id: str
    transcript: str = Field(min_length=1, max_length=20000)


class EditIn(BaseModel):
    subjective: str
    objective: str
    assessment: str
    plan: str = ""


def _allowed(note: dict[str, Any], user: dict[str, Any]) -> bool:
    return user["role"] != "user" or note["patient_id"] == user["id"]


def _public(note: dict[str, Any]) -> dict[str, Any]:
    note = dict(note)
    note["missing"] = load(note.pop("missing_json"))
    note["evidence"] = load(note.pop("evidence_json"))
    return note


def _clinical_checks(patient_id: str, transcript: str) -> dict[str, Any]:
    """Compare only recorded facts; absence stays explicit and is never inferred."""
    from src.medications.router import connection as medication_connection

    with medication_connection() as c:
        medicines = [
            load(r["payload"])["medicine"]
            for r in c.execute(
                "SELECT payload FROM plans WHERE patient_id=? AND status='approved'",
                (patient_id,),
            )
        ]
    hba1c = re.search(r"\b(?:hba1c|a1c)\s*(?:là|:|=)?\s*(\d+(?:[.,]\d+)?)\s*%", transcript, re.I)
    return {
        "approved_medications": medicines,
        "medication_status": "recorded" if medicines else "missing",
        "hba1c": hba1c.group(1).replace(",", ".") + "%" if hba1c else None,
        "hba1c_status": "transcript_only" if hba1c else "missing",
        "warning": "Chỉ đối chiếu dữ liệu đã ghi; bác sĩ phải xác minh, không dùng để tự đổi thuốc hoặc chẩn đoán.",
    }


@router.post("/drafts")
def create_draft(payload: DraftIn, user=Depends(get_current_user)):
    if user["role"] == "user" and payload.patient_id != user["id"]:
        raise HTTPException(403, "Forbidden")
    logs = get_logs(payload.patient_id, limit=20, days=90)
    transcript = payload.transcript.strip()
    symptom_lines = [s.strip() for s in re.split(r"[.!?\n]+", transcript) if s.strip()]
    missing = []
    if not logs:
        missing.append("chỉ số đường huyết")
    if not re.search(r"\b(thuốc|metformin|insulin|liều)\b", transcript, re.I):
        missing.append("thuốc đang dùng")
    if not re.search(r"\b(hba1c|a1c)\b", transcript, re.I):
        missing.append("HbA1c")
    latest = logs[0] if logs else None
    subjective = ("; ".join(symptom_lines[:4]) or "chưa ghi nhận") + " [Transcript]"
    objective = (f"Đường huyết gần nhất {latest['value_mgdl']} mg/dL [Log #{latest['id']}]" if latest else "chưa ghi nhận")
    assessment = "Dữ kiện được ghi nhận để bác sĩ đánh giá; không phải chẩn đoán. [Transcript]"
    evidence = [{"type": "transcript", "text": transcript}] + ([{"type": "glucose_log", "id": latest["id"]}] if latest else [])
    note_id = uid()
    created = now()
    with connect() as c:
        c.execute("INSERT INTO soap_notes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            note_id, payload.patient_id, transcript, subjective, objective, assessment, "",
            dump(missing), dump(evidence), "draft", 1, user["id"], None, created, None,
        ))
        c.execute("INSERT INTO soap_audit VALUES(?,?,?,?,?,?,?)", (uid(), note_id, user["id"], "created", None, dump({"subjective": subjective, "objective": objective, "assessment": assessment, "plan": ""}), created))
        note = row(c.execute("SELECT * FROM soap_notes WHERE id=?", (note_id,)).fetchone())
    return _public(note or {})


@router.get("/drafts/{note_id}")
def get_note(note_id: str, user=Depends(get_current_user)):
    with connect() as c:
        note = row(c.execute("SELECT * FROM soap_notes WHERE id=?", (note_id,)).fetchone())
    if not note:
        raise HTTPException(404, "SOAP note not found")
    if not _allowed(note, user):
        raise HTTPException(403, "Forbidden")
    return _public(note)


@router.put("/drafts/{note_id}")
def edit_note(note_id: str, payload: EditIn, user=Depends(require_role("doctor", "admin"))):
    with connect() as c:
        before = row(c.execute("SELECT * FROM soap_notes WHERE id=?", (note_id,)).fetchone())
        if not before:
            raise HTTPException(404, "SOAP note not found")
        if before["status"] != "draft":
            raise HTTPException(409, "Signed SOAP note is immutable")
        after = payload.model_dump()
        c.execute("UPDATE soap_notes SET subjective=?,objective=?,assessment=?,plan=?,version=version+1 WHERE id=?", (*after.values(), note_id))
        c.execute("INSERT INTO soap_audit VALUES(?,?,?,?,?,?,?)", (uid(), note_id, user["id"], "edited", dump({k: before[k] for k in after}), dump(after), now()))
    return get_note(note_id, user)


@router.post("/drafts/{note_id}/sign")
def sign_note(note_id: str, user=Depends(require_role("doctor", "admin"))):
    signed = now()
    with connect() as c:
        note = row(c.execute("SELECT * FROM soap_notes WHERE id=?", (note_id,)).fetchone())
        if not note:
            raise HTTPException(404, "SOAP note not found")
        if note["status"] != "draft":
            raise HTTPException(409, "SOAP note already signed")
        c.execute("UPDATE soap_notes SET status='signed',signed_by=?,signed_at=? WHERE id=?", (user["id"], signed, note_id))
        c.execute("INSERT INTO soap_audit VALUES(?,?,?,?,?,?,?)", (uid(), note_id, user["id"], "signed", None, dump({"signed_at": signed}), signed))
    return get_note(note_id, user)


@router.get("/drafts/{note_id}/review")
def review_note(note_id: str, user=Depends(require_role("doctor", "admin"))):
    note = get_note(note_id, user)
    with connect() as c:
        audit = [dict(r) for r in c.execute("SELECT actor_id,action,before_json,after_json,created_at FROM soap_audit WHERE note_id=? ORDER BY created_at", (note_id,))]
    for item in audit:
        item["before"] = load(item.pop("before_json")) if item["before_json"] else None
        item["after"] = load(item.pop("after_json")) if item["after_json"] else None
    created = next((item["after"] for item in audit if item["action"] == "created"), {})
    fields = ("subjective", "objective", "assessment", "plan")
    diff = [{"field": key, "before": created.get(key, ""), "after": note[key]} for key in fields if created.get(key, "") != note[key]]
    return {
        "note": note,
        "icd_suggestions": [{"code": "E11.x", "label": "Đái tháo đường týp 2 — chỉ tham khảo, bác sĩ kiểm chứng; không tự thêm vào SOAP", "source": ICD_SOURCE}],
        "clinical_checks": _clinical_checks(note["patient_id"], note["transcript"]),
        "diff": diff,
        "audit": audit,
    }


@router.get("/drafts/{note_id}/export")
def export_note(note_id: str, user=Depends(require_role("doctor", "admin"))):
    note = get_note(note_id, user)
    if note["status"] != "signed":
        raise HTTPException(409, "Only signed SOAP notes can be exported")
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - deployment dependency guard
        raise HTTPException(503, "PDF export is unavailable") from exc
    parts = ["<h1>SOAP BÀN GIAO</h1>"]
    for label, key in (("S", "subjective"), ("O", "objective"), ("A", "assessment"), ("P", "plan")):
        parts.append(f"<p><b>{label}:</b> {html.escape(note[key])}</p>")
    parts.append(f"<p><b>Ký bởi:</b> {html.escape(note['signed_by'])} lúc {html.escape(note['signed_at'])}</p>")
    document = fitz.open()
    page = document.new_page()
    page.insert_htmlbox(fitz.Rect(36, 36, 559, 806), "".join(parts))
    content = document.tobytes(garbage=4, deflate=True)
    document.close()
    return Response(content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="soap-{note_id}.pdf"'})
