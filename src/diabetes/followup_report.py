"""Descriptive coverage and trend signals for a type 2 diabetes follow-up report.

These calculations never infer HbA1c, diagnose disease, or set a treatment goal.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any


LOCAL_TIMEZONE = timezone(timedelta(hours=7))


def summarize_followup(logs: list[dict[str, Any]], days: int, end_date: date | None = None) -> dict[str, Any]:
    """List unrecorded dates and describe the most recent three consecutive days."""
    if days < 1:
        raise ValueError("days must be positive")
    end = end_date or datetime.now(LOCAL_TIMEZONE).date()
    start = end - timedelta(days=days - 1)
    by_day: dict[date, list[tuple[float, int]]] = defaultdict(list)
    for log in logs:
        try:
            measured_at = datetime.fromisoformat(str(log["measured_at"]).replace("Z", "+00:00"))
            measured = measured_at.astimezone(LOCAL_TIMEZONE).date() if measured_at.tzinfo else measured_at.date()
            value = float(log["value_mgdl"])
            log_id = int(log["id"])
        except (KeyError, TypeError, ValueError):
            continue
        if start <= measured <= end:
            by_day[measured].append((value, log_id))
    missing = [(start + timedelta(days=offset)).isoformat() for offset in range(days) if start + timedelta(days=offset) not in by_day]
    recent = [end - timedelta(days=2), end - timedelta(days=1), end]
    projection: dict[str, Any] = {
        "direction": "insufficient_data",
        "basis_log_ids": [],
        "limitation": "Chỉ là mô tả xu hướng từ nhật ký tự đo; không dự báo giá trị đường huyết, không suy HbA1c hay thay thế đánh giá của bác sĩ.",
    }
    if all(day in by_day for day in recent):
        averages = [sum(v for v, _ in by_day[day]) / len(by_day[day]) for day in recent]
        differences = [averages[1] - averages[0], averages[2] - averages[1]]
        if all(diff > 0 for diff in differences):
            direction = "up"
        elif all(diff < 0 for diff in differences):
            direction = "down"
        elif all(diff == 0 for diff in differences):
            direction = "flat"
        else:
            direction = "mixed"
        projection = {
            **projection,
            "direction": direction,
            "basis_log_ids": [log_id for day in recent for _, log_id in by_day[day]],
        }
    return {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "recorded_days": len(by_day),
        "missing_dates": missing,
        "trend_projection": projection,
    }
