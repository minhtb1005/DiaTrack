"""Conservative, review-only triage proposal for type 2 diabetes."""
from __future__ import annotations

from src.shared.glucose_policy import SCOPE_SOURCE, THRESHOLDS

TRIAGE_PROTOCOL_SOURCE = "docs/project_requirements.json#projects[258-triage].problem (protocol mô phỏng)"


def assess(symptoms: list[dict], glucose: float | None, onset: str | None) -> dict:
    """Return a question or a priority proposal; never a diagnosis or care order."""
    if glucose is not None and (glucose < THRESHOLDS["hypoglycemia"].value or glucose >= THRESHOLDS["critical_high"].value):
        return {
            "proposed_priority": "emergency",
            "review_status": "pending_clinician_review",
            "rationale": "Số đo gần nhất vượt ngưỡng cảnh báo khẩn. Đây chỉ là đề xuất phân luồng, không phải chẩn đoán.",
            "source": f"{TRIAGE_PROTOCOL_SOURCE}; {SCOPE_SOURCE}",
        }
    if not symptoms:
        question = "Bạn đang gặp triệu chứng gì (ví dụ: tê chân, mắt mờ, khát nhiều)?"
    elif glucose is None:
        question = "Số đo đường huyết gần nhất của bạn là bao nhiêu mg/dL?"
    elif not onset or not onset.strip():
        question = "Triệu chứng bắt đầu từ khi nào?"
    else:
        question = None
    if question:
        return {"followup_question": question, "review_status": "collecting"}

    codes = {str(item.get("code")) for item in symptoms}
    if glucose > THRESHOLDS["spike_high"].value or codes & {"neuropathy", "retinopathy"}:
        priority = "soon"
        reason = "Có chỉ số cần theo dõi hoặc triệu chứng cần nhân viên y tế xem xét."
    else:
        priority = "routine"
        reason = "Thông tin hiện có chưa chạm ngưỡng cảnh báo của hệ thống."
    return {
        "proposed_priority": priority,
        "review_status": "pending_clinician_review",
        "rationale": reason + " Đây chỉ là đề xuất phân luồng, không phải chẩn đoán.",
        "source": f"{TRIAGE_PROTOCOL_SOURCE}; {SCOPE_SOURCE}",
    }
