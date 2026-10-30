"""Doctor triage queue (glucose-only): GET /v1/doctor/patients.

Covers: 401 no-token, 403 role=user, 200 sort;
critical 300 > safe, with demo trend 110/125/142 not escalated,
per-user fail-open, glucose-only keys, no email leak.
"""
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def iso_glucose(monkeypatch):
    import src.diabetes.glucose_tracker as gt
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    monkeypatch.setattr(gt, "GLUCOSE_DB_PATH", Path(tmp.name))
    gt.init_glucose_db()
    yield Path(tmp.name)
    try:
        os.unlink(tmp.name)
    except Exception:
        pass


def _iso_day(offset: int) -> str:
    base = datetime.now(timezone.utc).replace(hour=7, minute=0, second=0, microsecond=0)
    return (base - timedelta(days=offset)).isoformat()


def _push(client: TestClient, hdr: dict, uid: str, value: float, off: int, notes=None):
    r = client.post("/v1/glucose", json={
        "user_id": uid, "value_mgdl": value, "context": "fasting",
        "measured_at": _iso_day(off), "notes": notes,
    }, headers=hdr)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _seed_three(client: TestClient, make_user):
    u_crit, t_crit = make_user(role="user")
    u_trend, t_trend = make_user(role="user")
    u_safe, t_safe = make_user(role="user")
    _push(client, {"Authorization": f"Bearer {t_crit}"}, u_crit["id"], 300, 0)
    for v, off in ((110, 2), (125, 1), (142, 0)):
        _push(client, {"Authorization": f"Bearer {t_trend}"}, u_trend["id"], v, off)
    _push(client, {"Authorization": f"Bearer {t_safe}"}, u_safe["id"], 100, 0)
    return u_crit, u_trend, u_safe


class TestDoctorPatients:
    def test_tracker_advice_waits_for_doctor_approval(self, client: TestClient, make_user, doctor_user, monkeypatch):
        patient, token = make_user(role="user")
        import src.chat.rag_pipeline as pipeline
        import src.chat.router as chat_router

        draft = "Bản nháp diễn giải xu hướng, chưa được bác sĩ duyệt."
        def fake_rag(*args, **kwargs):
            assert kwargs["defer_publication"] is True
            return {
                "raw_answer": {"answer": draft, "cited_sources": [1]},
                "contexts": [{"source_id": "WHO-HEARTS-D", "file_name": "WHO_HEARTS-D_2020.pdf", "content": "Dữ liệu tham khảo", "page_numbers": [12]}],
                "trace_id": None, "prompt_version": "test", "cache_hit": False, "timings": {},
            }
        monkeypatch.setattr(pipeline, "rag_chat", fake_rag)
        monkeypatch.setattr(chat_router, "evaluate_rag", lambda *args, **kwargs: {
            "is_low_confidence": False, "confidence": 0.9, "routed_role": "pharmacist", "failed_metrics": [],
        })
        patient_hdr = {"Authorization": f"Bearer {token}"}
        doctor_hdr = {"Authorization": f"Bearer {doctor_user['token']}"}
        response = client.post("/v1/query", json={
            "query": "Diễn giải xu hướng đường huyết gần đây", "user_id": patient["id"],
            "require_doctor_review": True,
        }, headers=patient_hdr)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "pending_review"
        assert body["answer"] == "Bản diễn giải đang chờ bác sĩ duyệt trước khi hiển thị."
        assert draft not in response.text
        review_id = body["review_id"]
        pending = client.get(f"/v1/reviews/{review_id}", headers=patient_hdr)
        assert pending.status_code == 200
        assert "draft_answer" not in pending.json()
        other, other_token = make_user(role="user")
        assert client.get(f"/v1/reviews/{review_id}", headers={"Authorization": f"Bearer {other_token}"}).status_code == 403
        queue = client.get(f"/v1/reviews/{review_id}", headers=doctor_hdr)
        assert queue.status_code == 200
        assert queue.json()["routed_role"] == "doctor"
        assert queue.json()["draft_answer"] == draft
        pharmacist, pharmacist_token = make_user(role="pharmacist")
        pharmacist_hdr = {"Authorization": f"Bearer {pharmacist_token}"}
        assert client.get(f"/v1/reviews/{review_id}", headers=pharmacist_hdr).status_code == 403
        assert client.post(f"/v1/reviews/{review_id}/decide", json={"decision": "approved"}, headers=pharmacist_hdr).status_code == 403
        approved = client.post(f"/v1/reviews/{review_id}/decide", json={"decision": "approved"}, headers=doctor_hdr)
        assert approved.status_code == 200
        history = client.get("/v1/query/history", headers=patient_hdr)
        assert next(h for h in history.json()["history"] if h.get("review_id") == review_id)["answer"] == draft

        monkeypatch.setattr(chat_router, "create_review_request", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("queue unavailable")))
        failed = client.post("/v1/query", json={
            "query": "Diễn giải xu hướng đường huyết gần đây", "user_id": patient["id"],
            "require_doctor_review": True,
        }, headers=patient_hdr)
        assert failed.status_code == 503
        assert draft not in failed.text

    def test_spike_280_is_watch_not_critical(self, client: TestClient, make_user, doctor_user, iso_glucose):
        patient, token = make_user(role="user")
        _push(client, {"Authorization": f"Bearer {token}"}, patient["id"], 280, 0)
        hdr = {"Authorization": f"Bearer {doctor_user['token']}"}
        response = client.get("/v1/doctor/patients", headers=hdr)
        assert response.status_code == 200
        row = next(p for p in response.json()["patients"] if p["user_id"] == patient["id"])
        assert row["level"] == "watch"

    def test_legacy_high_display_band_is_not_watch(self, client: TestClient, make_user, doctor_user, iso_glucose):
        patient, token = make_user(role="user")
        _push(client, {"Authorization": f"Bearer {token}"}, patient["id"], 130, 0)
        hdr = {"Authorization": f"Bearer {doctor_user['token']}"}
        response = client.get("/v1/doctor/patients", headers=hdr)
        assert response.status_code == 200
        row = next(p for p in response.json()["patients"] if p["user_id"] == patient["id"])
        assert row["level"] == "safe"

    def test_401_no_token(self, client: TestClient, iso_glucose):
        # session-scoped TestClient shares its cookie jar with prior tests that
        # logged in, so clear cookies to simulate a truly unauthenticated request.
        client.cookies.clear()
        r = client.get("/v1/doctor/patients")
        assert r.status_code == 401, r.text

    def test_403_user_role(self, client: TestClient, make_user, iso_glucose):
        user, tok = make_user(role="user")
        r = client.get("/v1/doctor/patients", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 403, r.text

    def test_demo_trend_does_not_raise_queue_priority(self, client: TestClient, make_user, doctor_user, iso_glucose):
        u_crit, u_trend, u_safe = _seed_three(client, make_user)
        hdr = {"Authorization": f"Bearer {doctor_user['token']}"}
        r = client.get("/v1/doctor/patients", headers=hdr)
        assert r.status_code == 200, r.text
        patients = r.json()["patients"]
        levels = {p["user_id"]: p["level"] for p in patients}
        assert levels == {u_crit["id"]: "critical", u_trend["id"]: "safe", u_safe["id"]: "safe"}
        assert patients[0]["user_id"] == u_crit["id"]

    def test_fail_open_one_user_broken(self, client: TestClient, make_user, doctor_user, iso_glucose, monkeypatch):
        u_crit, u_trend, u_safe = _seed_three(client, make_user)
        import src.diabetes.glucose_tracker as gt
        orig = gt.get_logs

        def flaky(uid, limit=50, days=None):
            if uid == u_trend["id"]:
                raise RuntimeError("boom")
            return orig(uid, limit=limit, days=days)

        monkeypatch.setattr(gt, "get_logs", flaky)
        hdr = {"Authorization": f"Bearer {doctor_user['token']}"}
        r = client.get("/v1/doctor/patients", headers=hdr)
        assert r.status_code == 200, r.text
        patients = r.json()["patients"]
        assert len(patients) == 3
        row = next(p for p in patients if p["user_id"] == u_trend["id"])
        assert row["level"] == "safe"

    def test_glucose_only_keys_no_email(self, client: TestClient, make_user, doctor_user, iso_glucose):
        _seed_three(client, make_user)
        hdr = {"Authorization": f"Bearer {doctor_user['token']}"}
        r = client.get("/v1/doctor/patients", headers=hdr)
        assert r.status_code == 200, r.text
        assert "email" not in r.text
        allowed = {"user_id", "username", "last_value", "last_classification",
                   "last_measured_at", "level", "should_escalate", "anomaly_count"}
        for p in r.json()["patients"]:
            assert set(p.keys()) <= allowed, set(p.keys()) - allowed
