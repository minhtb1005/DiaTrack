"""LLM summarizer for guideline diff & safety alerts — tiếng Việt mặc định"""
from __future__ import annotations
import json
import os
from typing import Dict, Any, Optional

try:
    from src.shared.prompt_manager import get_system_prompt
    from src.shared.config import DEFAULT_MODEL
except ImportError:
    from shared.prompt_manager import get_system_prompt  # type: ignore
    from shared.config import DEFAULT_MODEL  # type: ignore

def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 1200) -> str:
    try:
        from src.shared.nvidia import llm_client
    except ImportError:
        from shared.nvidia import llm_client  # type: ignore
    client = llm_client()
    if client is None:
        raise RuntimeError("Kh\u00f4ng c\u00f3 NVIDIA key")
    model = DEFAULT_MODEL
    if model.startswith("openai/"):
        model = model.split("/", 1)[1]
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


def _summarize_or_fallback(system: str, user: str, max_tokens: int, defaults: Dict[str, Any]) -> Dict[str, Any]:
    """Shared LLM JSON call + setdefaults (throws to caller fallback)."""
    raw = _call_llm(system, user, max_tokens=max_tokens)
    parsed = json.loads(raw)
    for k, v in defaults.items():
        parsed.setdefault(k, v)
    return parsed

def summarize_guideline_diff(
    source: str,
    title: str,
    old_text: Optional[str],
    new_text: str,
    version_hint: Optional[str] = None,
    publication_date_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """Return structured diff JSON (VI). Falls back to heuristic if LLM unavailable."""
    from src.shared.privacy import redact_text
    old_text = redact_text(old_text or "")
    new_text = redact_text(new_text)
    system = get_system_prompt("guideline_diff")
    user = (
        f"Nguồn: {source}\nTiêu đề: {title}\n"
        f"Version gợi ý: {version_hint or 'không rõ'}\n"
        f"Ngày XB gợi ý: {publication_date_hint or 'không rõ'}\n\n"
        f"--- TRÍCH ĐOẠN CŨ (có thể rỗng nếu là bản đầu) ---\n{(old_text or '')[:6000]}\n\n"
        f"--- TRÍCH ĐOẠN MỚI ---\n{new_text[:8000]}\n\n"
        "Hãy trả về JSON đúng schema đã mô tả trong system prompt."
    )
    try:
        return _summarize_or_fallback(system, user, 1500, {
            "tom_tat_tieng_viet": "",
            "changed_sections": [],
            "dosage_changes": [],
            "new_recommendations": [],
            "removed_recommendations": [],
            "version_phat_hien": version_hint or "",
            "ngay_xuat_ban": publication_date_hint or "",
            "muc_do_quan_trong": "medium",
        })
    except Exception as e:
        from src.shared.privacy import PrivacyError
        if isinstance(e, PrivacyError):
            raise
        # heuristic fallback — still VI
        snippet = new_text[:500].replace("\n", " ")
        return {
            "tom_tat_tieng_viet": f"[Heuristic] Phát hiện bản mới {title} ({source}). Trích: {snippet[:200]}... (LLM lỗi: {str(e)[:120]})",
            "changed_sections": [],
            "dosage_changes": [],
            "new_recommendations": [],
            "removed_recommendations": [],
            "version_phat_hien": version_hint or "",
            "ngay_xuat_ban": publication_date_hint or "",
            "muc_do_quan_trong": "medium",
            "_fallback": True,
            "_error": str(e)[:500],
        }

def summarize_safety_alert(raw_json: Dict[str, Any], source: str) -> Dict[str, Any]:
    """Summarize FDA/DAV/MOH raw alert into VI JSON."""
    system = get_system_prompt("safety_summary")
    from src.shared.privacy import sanitize
    raw_json = sanitize(raw_json)
    user = f"Nguồn: {source}\nDữ liệu thô (JSON):\n{json.dumps(raw_json, ensure_ascii=False)[:7000]}\n\nTrả về JSON đúng schema safety_summary."
    try:
        return _summarize_or_fallback(system, user, 1000, {
            "tieu_de_vi": raw_json.get("alert_title") or "Cảnh báo an toàn thuốc",
            "tom_tat_vi": "",
            "thuoc_lien_quan": [],
            "loai_canh_bao": "recall",
            "muc_do": "medium",
            "ly_do": "",
            "khuyen_cao": "",
            "nguon": source,
            "diem_rui_ro": 0.5,
        })
    except Exception as e:
        # heuristic
        title = raw_json.get("alert_title") or raw_json.get("title") or "Cảnh báo"
        drug = raw_json.get("drug_name") or raw_json.get("product_description") or ""
        return {
            "tieu_de_vi": title,
            "tom_tat_vi": f"[Heuristic] Cảnh báo từ {source}: {title} — thuốc: {drug} (LLM lỗi: {str(e)[:120]})",
            "thuoc_lien_quan": [drug] if drug else [],
            "loai_canh_bao": raw_json.get("alert_type", "recall"),
            "muc_do": raw_json.get("severity", "medium"),
            "ly_do": str(raw_json.get("reason_for_recall") or raw_json.get("reason") or "")[:300],
            "khuyen_cao": "Tham khảo dược sĩ/bác sĩ trước khi tiếp tục sử dụng.",
            "nguon": source,
            "diem_rui_ro": 0.5,
            "_fallback": True,
            "_error": str(e)[:500],
        }
