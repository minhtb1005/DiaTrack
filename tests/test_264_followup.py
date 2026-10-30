"""Coverage and non-clinical trend reporting for project 264."""

from datetime import date, datetime, timedelta, timezone

from src.diabetes.followup_report import summarize_followup
from src.diabetes.glucose_tracker import add_log
from src.diabetes.soap_summary import generate_soap, soap_to_markdown


def _record(log_id: int, day: str, value: float) -> dict:
    return {"id": log_id, "measured_at": f"{day}T07:00:00+00:00", "value_mgdl": value}


def test_missing_dates_are_explicit_and_never_filled():
    report = summarize_followup([_record(1, "2026-10-27", 110), _record(2, "2026-10-29", 120)], 3, date(2026, 10, 29))
    assert report["missing_dates"] == ["2026-10-28"]
    assert report["recorded_days"] == 2
    assert report["trend_projection"]["direction"] == "insufficient_data"
    assert report["trend_projection"]["basis_log_ids"] == []


def test_three_consecutive_days_describe_direction_with_log_sources():
    logs = [_record(1, "2026-10-27", 100), _record(2, "2026-10-28", 110), _record(3, "2026-10-29", 120)]
    report = summarize_followup(logs, 3, date(2026, 10, 29))
    assert report["missing_dates"] == []
    assert report["trend_projection"]["direction"] == "up"
    assert report["trend_projection"]["basis_log_ids"] == [1, 2, 3]
    assert "không suy HbA1c" in report["trend_projection"]["limitation"]


def test_utc_measurement_uses_vietnam_calendar_day():
    report = summarize_followup([{"id": 7, "measured_at": "2026-10-28T18:00:00+00:00", "value_mgdl": 110}], 1, date(2026, 10, 29))
    assert report["recorded_days"] == 1
    assert report["missing_dates"] == []


def test_soap_report_does_not_infer_hba1c_or_treatment(temp_user, mock_openai):
    now = datetime.now(timezone.utc).replace(hour=7, minute=0, second=0, microsecond=0)
    for offset, value in ((2, 100), (1, 110), (0, 120)):
        add_log(temp_user, value, measured_at=now - timedelta(days=offset), context="fasting")
    data = generate_soap(temp_user, days=3)
    assessment = data["soap"]["assessment"]
    assert "không thể kết luận đạt hay chưa đạt" in assessment
    assert "154" not in assessment
    assert data["soap"]["plan"] == ""
    assert data["followup"]["trend_projection"]["direction"] == "up"
    markdown = soap_to_markdown(data)
    assert "Ngày chưa có bản ghi" in markdown
    assert "[Xem log #" in markdown
    assert "không suy HbA1c" in markdown


def test_soap_api_exposes_coverage_without_hba1c_inference(client, auth_header, mock_openai):
    user_id = auth_header["user"]["id"]
    headers = {"Authorization": f"Bearer {auth_header['token']}"}
    logged = client.post("/v1/glucose", json={"user_id": user_id, "value_mgdl": 110, "context": "fasting"}, headers=headers)
    assert logged.status_code == 200, logged.text
    response = client.post("/v1/soap/generate", json={"user_id": user_id, "days": 3, "disease": "diabetes"}, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["followup"]["recorded_days"] >= 1
    assert isinstance(body["followup"]["missing_dates"], list)
    assert body["followup"]["trend_projection"]["direction"] == "insufficient_data"
    assert "không thể kết luận đạt hay chưa đạt" in body["soap"]["assessment"]
    assert body["soap"]["plan"] == ""
