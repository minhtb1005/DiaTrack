"""
Hướng A — Trợ lý tuân thủ tự theo dõi đường huyết.

- Lưu log vào SQLite (metadata/glucose_logs.db — legacy) / vitals.db via BaseTracker helpers
- Dải phân loại hiển thị legacy (chưa xác minh lâm sàng cho đo tại nhà)
- Thống kê, streak, logs_per_week (KPI: ≥3 lần/tuần)
- Cảnh báo khẩn theo <70 / ≥300; dải hiển thị cũ không quyết định escalation
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from src.shared.glucose_policy import THRESHOLDS, glucose_severity

try:
    from src.shared.config import GLUCOSE_DB_PATH as _DEFAULT_GLUCOSE_DB_PATH
    from src.vitals.base_tracker import get_conn as _base_get_conn, init_table, fetch_logs, classification_counts, calc_streak, calc_logs_per_week
except ImportError:  # pragma: no cover
    from shared.config import GLUCOSE_DB_PATH as _DEFAULT_GLUCOSE_DB_PATH  # type: ignore
    from vitals.base_tracker import get_conn as _base_get_conn, init_table, fetch_logs, classification_counts, calc_streak, calc_logs_per_week  # type: ignore

# Module-namespace patchable + env-overridable (tests cách ly DB dev)
GLUCOSE_DB_PATH = Path(os.getenv("GLUCOSE_DB_PATH", str(_DEFAULT_GLUCOSE_DB_PATH)))

# ---------- DB ----------

def init_glucose_db():
    init_table(
        GLUCOSE_DB_PATH,
        """
        CREATE TABLE IF NOT EXISTS glucose_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            value_mgdl REAL NOT NULL,
            measured_at TEXT NOT NULL,
            context TEXT NOT NULL DEFAULT 'random',
            notes TEXT,
            classification TEXT,
            created_at TEXT NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_glucose_user_time ON glucose_logs(user_id, measured_at)",
    )


# ---------- Classification ----------

def classify_glucose(value_mgdl: float, context: str) -> Tuple[str, str]:
    """
    Returns (classification, message).
    classification in: low | no_alert | alert_high | critical
    """
    severity = glucose_severity(value_mgdl, context)
    if severity == "low":
        return severity, f"Chỉ số dưới {THRESHOLDS['hypoglycemia'].value:g} mg/dL — liên hệ cơ sở y tế ngay; nếu có triệu chứng nặng, gọi 115."
    if severity == "critical":
        return severity, f"Chỉ số từ {THRESHOLDS['critical_high'].value:g} mg/dL — liên hệ cơ sở y tế ngay; nếu có triệu chứng nặng, gọi 115."
    if severity == "alert_high":
        return severity, f"Chỉ số trên {THRESHOLDS['spike_high'].value:g} mg/dL — liên hệ bác sĩ để được hướng dẫn; không tự đổi liều thuốc hoặc insulin."
    return severity, "Chưa chạm ngưỡng cảnh báo của hệ thống; điều này không xác nhận chỉ số đạt mục tiêu cá nhân. Hãy đối chiếu với mục tiêu bác sĩ đã đặt."


def should_escalate_to_doctor(user_id: str, lookback: int = 3) -> bool:
    """Escalate urgent readings only; legacy display bands are not care thresholds."""
    logs = get_logs(user_id, limit=lookback)
    if not logs:
        return False
    if any(l["classification"] == "critical" or l["classification"] == "low" for l in logs):
        return True
    return False


# ---------- CRUD ----------

def add_log(user_id: str, value_mgdl: float, measured_at: Optional[datetime] = None,
            context: str = "random", notes: Optional[str] = None) -> Dict[str, Any]:
    init_glucose_db()
    measured_at = measured_at or datetime.now(timezone.utc)
    classification, message = classify_glucose(value_mgdl, context)
    conn = _base_get_conn(GLUCOSE_DB_PATH)
    cur = conn.execute(
        "INSERT INTO glucose_logs (user_id, value_mgdl, measured_at, context, notes, classification, created_at) VALUES (?,?,?,?,?,?,?)",
        (user_id, value_mgdl, measured_at.isoformat(), context, notes, classification, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return {
        "id": row_id,
        "user_id": user_id,
        "value_mgdl": value_mgdl,
        "measured_at": measured_at,
        "context": context,
        "notes": notes,
        "classification": classification,
        "message": message,
    }


def get_logs(user_id: str, limit: int = 50, days: Optional[int] = None) -> List[Dict[str, Any]]:
    init_glucose_db()
    rows = fetch_logs(GLUCOSE_DB_PATH, "glucose_logs", user_id, limit, days)
    # Keep original projection for backward compat (tests expect these 7 keys)
    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "user_id": r["user_id"],
            "value_mgdl": r["value_mgdl"],
            "measured_at": r["measured_at"],
            "context": r["context"],
            "notes": r["notes"],
            # Stored legacy labels are not clinical evidence; re-evaluate on read.
            "classification": glucose_severity(r["value_mgdl"], r["context"]),
        })
    return out


def get_stats(user_id: str) -> Dict[str, Any]:
    logs = get_logs(user_id, limit=1000)
    total = len(logs)
    if total == 0:
        return {
            "user_id": user_id,
            "total_logs": 0,
            "avg_mgdl": None,
            "last_7_days_avg": None,
            "streak_days": 0,
            "logs_per_week": 0.0,
            "classification_counts": {},
        }
    vals = [l["value_mgdl"] for l in logs]
    avg = sum(vals) / len(vals)
    seven = [l for l in logs if l["measured_at"] >= (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()]
    last7_avg = sum(l["value_mgdl"] for l in seven) / len(seven) if seven else None
    counts = classification_counts(logs)
    streak = calc_streak(logs)
    logs_per_week = calc_logs_per_week(logs)
    return {
        "user_id": user_id,
        "total_logs": total,
        "avg_mgdl": round(avg, 1),
        "last_7_days_avg": round(last7_avg, 1) if last7_avg else None,
        "streak_days": streak,
        "logs_per_week": logs_per_week,
        "classification_counts": counts,
    }


def needs_attention_summary(user_id: str) -> str:
    stats = get_stats(user_id)
    escalate = should_escalate_to_doctor(user_id)
    logs = get_logs(user_id, limit=7)
    if not logs:
        return "Chưa có dữ liệu đường huyết — hãy nhập lần đo đầu tiên."
    last = logs[0]
    base = f"Lần đo gần nhất: {last['value_mgdl']} mg/dL ({last['classification']}) lúc {last['measured_at'][:16]} [{last['context']}]. "
    base += f"Trung bình 7 ngày: {stats['last_7_days_avg'] or '—'} mg/dL. Tần suất: {stats['logs_per_week']}/tuần. "
    if escalate:
        base += "⚠️ Khuyến nghị liên hệ nhân viên y tế vì có số đo dưới 70 hoặc từ 300 mg/dL."
    elif stats["logs_per_week"] < 3:
        base += "Gợi ý demo ≥3 lần/tuần, chưa được duyệt lâm sàng; theo lịch bác sĩ hướng dẫn."
    return base
