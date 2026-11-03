"""Real HTTP-to-SQLite integration checks for the first seven task flows.

The shared client fixture redirects auth and glucose writes to temporary DBs.
These checks complement, but do not replace, browser integration acceptance.
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_tasks_1_2_glucose_boundaries_ownership_and_db(client, make_user):
    from src.diabetes import glucose_tracker

    patient, token = make_user()
    _, other_token = make_user()
    headers = _headers(token)
    instant = "2026-10-27T07:00:00+07:00"
    expected = {69: "low", 70: "no_alert", 110: "no_alert", 250: "no_alert",
                251: "alert_high", 299: "alert_high", 300: "critical"}
    ids = []
    for value, label in expected.items():
        response = client.post("/v1/glucose", headers=headers, json={
            "user_id": patient["id"], "value_mgdl": value,
            "context": "fasting", "measured_at": instant,
        })
        assert response.status_code == 200, response.text
        item = response.json()
        ids.append(item["id"])
        assert (item["value_mgdl"], item["context"], item["classification"]) == (value, "fasting", label)
        assert item["measured_at"] == instant
        if value in (69, 300):
            assert "liên hệ cơ sở y tế ngay" in item["message"]
        else:
            assert "liên hệ cơ sở y tế ngay" not in item["message"]
        assert "tự đổi liều" not in item["message"] or "không tự đổi liều" in item["message"]

    listed = client.get(f"/v1/glucose/{patient['id']}", headers=headers)
    assert listed.status_code == 200
    by_id = {row["id"]: row for row in listed.json()["logs"]}
    assert all(by_id[record_id]["value_mgdl"] == value for record_id, value in zip(ids, expected))
    with sqlite3.connect(glucose_tracker.GLUCOSE_DB_PATH) as db:
        rows = db.execute("SELECT id, user_id, value_mgdl, measured_at FROM glucose_logs WHERE user_id=?", (patient["id"],)).fetchall()
    assert len(rows) == len(expected)
    assert {row[0] for row in rows} == set(ids)
    assert all(row[1] == patient["id"] and row[3] == instant for row in rows)

    assert client.get(f"/v1/glucose/{patient['id']}", headers=_headers(other_token)).status_code == 403
    assert client.post("/v1/glucose", headers=_headers(other_token), json={
        "user_id": patient["id"], "value_mgdl": 110,
    }).status_code == 403
    for invalid in ({"user_id": patient["id"], "context": "fasting"},
                    {"user_id": patient["id"], "value_mgdl": "bad"}):
        assert client.post("/v1/glucose", headers=headers, json=invalid).status_code == 422
    with sqlite3.connect(glucose_tracker.GLUCOSE_DB_PATH) as db:
        assert db.execute("SELECT count(*) FROM glucose_logs WHERE user_id=?", (patient["id"],)).fetchone()[0] == len(expected)


def test_tasks_3_5_source_logs_missing_day_and_soap(client, make_user):
    patient, token = make_user()
    headers = _headers(token)
    now = datetime.now(timezone.utc).replace(hour=7, minute=0, second=0, microsecond=0)
    ids = []
    for days_ago, value in ((2, 110), (0, 120)):
        posted = client.post("/v1/glucose", headers=headers, json={
            "user_id": patient["id"], "value_mgdl": value,
            "context": "fasting", "measured_at": (now - timedelta(days=days_ago)).isoformat(),
        })
        assert posted.status_code == 200, posted.text
        ids.append(posted.json()["id"])
    logs = client.get(f"/v1/glucose/{patient['id']}", headers=headers).json()["logs"]
    assert {row["id"] for row in logs} == set(ids)
    response = client.post("/v1/soap/generate", headers=headers, json={
        "user_id": patient["id"], "days": 3, "disease": "diabetes",
    })
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["followup"]["recorded_days"] == 2
    assert report["followup"]["missing_dates"]
    assert report["followup"]["trend_projection"]["direction"] == "insufficient_data"
    assert report["followup"]["trend_projection"]["basis_log_ids"] == []
    assert report["soap"]["plan"] == ""
    assert "không thể kết luận đạt hay chưa đạt" in report["soap"]["assessment"]
    markdown = client.post("/v1/soap/generate/markdown", headers=headers, json={
        "user_id": patient["id"], "days": 3, "disease": "diabetes",
    })
    assert markdown.status_code == 200, markdown.text
    assert "Ngày chưa có bản ghi" in markdown.text
    assert any(f"[Xem log #{record_id}" in markdown.text for record_id in ids)


def test_task_4_doctor_dashboard_reads_patient_logs_and_enforces_role(client, make_user, doctor_user):
    from src.diabetes import glucose_tracker

    patients = [make_user() for _ in range(2)]
    for (patient, token), value in zip(patients, (280, 300)):
        response = client.post("/v1/glucose", headers=_headers(token), json={
            "user_id": patient["id"], "value_mgdl": value,
            "context": "fasting", "measured_at": "2026-10-27T07:00:00+07:00",
        })
        assert response.status_code == 200, response.text
    doctor_response = client.get("/v1/doctor/patients", headers=_headers(doctor_user["token"]))
    assert doctor_response.status_code == 200, doctor_response.text
    rows = {row["user_id"]: row for row in doctor_response.json()["patients"]}
    assert rows[patients[0][0]["id"]]["level"] == "watch"
    assert rows[patients[1][0]["id"]]["level"] == "critical"
    assert client.get("/v1/doctor/patients", headers=_headers(patients[0][1])).status_code == 403
    with sqlite3.connect(glucose_tracker.GLUCOSE_DB_PATH) as db:
        for (patient, _), value in zip(patients, (280, 300)):
            assert db.execute(
                "SELECT value_mgdl FROM glucose_logs WHERE user_id=?", (patient["id"],)
            ).fetchone()[0] == value


def test_tasks_6_7_structured_and_emergency_before_scope(client, monkeypatch, tmp_path):
    monkeypatch.setenv("TRIAGE_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("TRIAGE_EVENTS_PATH", str(tmp_path / "events.jsonl"))
    for _k in (
        "NVDIA_API_KEY", "NVDIA_API_KEY2", "NVDIA_API_KEY3",
        "NVIDIA_API_KEY", "NVIDIA_API_KEY2", "NVIDIA_API_KEY3",
    ):
        monkeypatch.delenv(_k, raising=False)
    # The session-scoped client retains prior login cookies. This path checks the
    # anonymous structured proposal; authenticated patients receive a redacted
    # pending-review response from the current HITL queue.
    client.cookies.clear()
    missing = client.post("/v1/triage", json={"message": "tê chân, mắt mờ", "structured": True})
    assert missing.status_code == 200, missing.text
    assert missing.json()["followup_question"]
    complete = client.post("/v1/triage", json={
        "message": "tê chân, mắt mờ", "structured": True,
        "latest_glucose_mgdl": 180, "symptom_onset": "hôm qua",
    })
    assert complete.status_code == 200, complete.text
    proposal = complete.json()
    assert proposal["proposed_priority"] in ("routine", "soon", "emergency")
    assert proposal["review_status"] == "pending_clinician_review"
    assert proposal["recommended_doctors"] == []
    for message in ("vã mồ hôi, lơ mơ", "va mo hoi, lo mo",
                    "thở nhanh, hơi thở mùi xeton", "tho nhanh, hoi tho mui xeton",
                    "bàn chân sưng đỏ, chảy mủ", "ban chan sung do, chay mu",
                    "đau ngực, méo miệng", "dau nguc, meo mieng"):
        result = client.post("/v1/triage", json={"message": message, "structured": True})
        assert result.status_code == 200, result.text
        assert result.json()["emergency"] is True
        assert "115" in result.json()["message"]
        assert result.json()["recommended_doctors"] == []
    for value in (69, 300):
        result = client.post("/v1/triage", json={
            "message": "hỏi về huyết áp", "structured": True, "latest_glucose_mgdl": value,
        })
        assert result.status_code == 200
        assert result.json()["emergency"] is True
        assert "115" in result.json()["message"]
    scope = json.loads(Path("docs/project_requirements.json").read_text(encoding="utf-8"))["scope_rules"]
    refused = client.post("/v1/triage", json={"message": "hỏi về huyết áp", "structured": True})
    assert refused.status_code == 200
    assert refused.json()["message"] == scope["out_of_scope_reply"]
