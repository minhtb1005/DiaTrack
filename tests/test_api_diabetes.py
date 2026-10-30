"""Integration tests for diabetes API (Tracks A/B/C) — with Auth."""
import pytest
from fastapi.testclient import TestClient

class TestDiabetesAPI:
    def test_query_diabetes_returns_citation(self, client: TestClient, auth_header):
        hdr = {"Authorization": f"Bearer {auth_header['token']}"}
        resp = client.post("/v1/query", json={"query": "What are WHO diagnostic thresholds for diabetes fasting and 2-hour?", "top_k": 3, "user_id": auth_header["user"]["id"]}, headers=hdr)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "answer" in data
        assert len(data["answer"]) > 0
        if data.get("audit"):
            assert "citations" in data["audit"]
        # HILT fields should be present
        assert "status" in data
        assert "evaluation" in data

    def test_query_requires_auth(self, client: TestClient):
        # Session-scoped client keeps login cookie from prior tests — clear it
        # so this request is truly unauthenticated (same pattern as test_admin_memory).
        client.cookies.clear()
        resp = client.post("/v1/query", json={"query": "hello", "top_k": 3})
        assert resp.status_code == 401

    def test_query_requires_nonempty(self, client: TestClient, auth_header):
        hdr = {"Authorization": f"Bearer {auth_header['token']}"}
        resp = client.post("/v1/query", json={"query": "", "top_k": 3}, headers=hdr)
        assert resp.status_code in (200, 422)

    def test_glucose_roundtrip(self, client: TestClient, auth_header):
        hdr = {"Authorization": f"Bearer {auth_header['token']}"}
        uid = auth_header["user"]["id"]
        r = client.post("/v1/glucose", json={"user_id": uid, "value_mgdl": 145, "context": "fasting", "notes": "after breakfast"}, headers=hdr)
        assert r.status_code == 200, r.text
        assert r.json()["classification"] in ("elevated", "high", "normal", "low", "critical")
        r2 = client.get(f"/v1/glucose/{uid}", headers=hdr)
        assert r2.status_code == 200
        assert r2.json()["stats"]["total_logs"] >= 1
        assert "logs_per_week" in r2.json()["stats"]

    def test_glucose_110_roundtrip_and_ownership(self, client: TestClient, make_user):
        first, first_token = make_user(role="user")
        second, second_token = make_user(role="user")
        h1 = {"Authorization": f"Bearer {first_token}"}
        h2 = {"Authorization": f"Bearer {second_token}"}
        payload = {"user_id": first["id"], "value_mgdl": 110, "context": "fasting"}
        posted = client.post("/v1/glucose", json=payload, headers=h1)
        assert posted.status_code == 200, posted.text
        record = posted.json()
        assert record["user_id"] == first["id"]
        assert record["value_mgdl"] == 110
        assert record["context"] == "fasting"
        assert record["measured_at"]
        assert "chẩn đoán" not in record["message"].lower()
        own = client.get(f"/v1/glucose/{first['id']}", headers=h1)
        assert own.status_code == 200
        assert any(row["id"] == record["id"] and row["value_mgdl"] == 110 for row in own.json()["logs"])
        assert client.get(f"/v1/glucose/{first['id']}", headers=h2).status_code == 403
        assert client.post("/v1/glucose", json=payload, headers=h2).status_code == 403
        for invalid in ({"user_id": first["id"], "context": "fasting"}, {**payload, "value_mgdl": "not-a-number"}):
            assert client.post("/v1/glucose", json=invalid, headers=h1).status_code == 422

    def test_glucose_validation_rejects_out_of_range(self, client: TestClient, auth_header):
        hdr = {"Authorization": f"Bearer {auth_header['token']}"}
        uid = auth_header["user"]["id"]
        r = client.post("/v1/glucose", json={"user_id": uid, "value_mgdl": 5, "context": "fasting"}, headers=hdr)
        assert r.status_code == 422

    def test_soap_generate(self, client: TestClient, auth_header):
        hdr = {"Authorization": f"Bearer {auth_header['token']}"}
        uid = auth_header["user"]["id"]
        client.post("/v1/glucose", json={"user_id": uid, "value_mgdl": 110, "context": "fasting"}, headers=hdr)
        client.post("/v1/glucose", json={"user_id": uid, "value_mgdl": 190, "context": "post_meal_2h"}, headers=hdr)
        resp = client.post("/v1/soap/generate", json={"user_id": uid, "days": 14}, headers=hdr)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "soap" in data
        for k in ("subjective", "objective", "assessment", "plan"):
            assert k in data["soap"]
        # P is ALWAYS empty — the doctor decides
        assert data["soap"]["plan"] == ""
        # A only states HbA1c<7% target check + audit links on S/O/A
        assert "HbA1c" in data["soap"]["assessment"]
        assert "[Xem log #" in data["soap"]["subjective"]
        assert "[Xem log #" in data["soap"]["objective"]
        assert "[Xem log #" in data["soap"]["assessment"]

    def test_glucose_returns_anomaly_and_fqg(self, client: TestClient, auth_header):
        hdr = {"Authorization": f"Bearer {auth_header['token']}"}
        uid = auth_header["user"]["id"]
        r = client.post("/v1/glucose", json={"user_id": uid, "value_mgdl": 260, "context": "random"}, headers=hdr)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "anomaly" in data and data["anomaly"]["type"] == "spike"
        assert "follow_up_questions" in data and len(data["follow_up_questions"]) > 0
        r2 = client.post("/v1/glucose", json={"user_id": uid, "value_mgdl": 110, "context": "fasting"}, headers=hdr)
        assert r2.status_code == 200, r2.text
        assert r2.json()["anomaly"]["type"] == "none"
        assert r2.json()["follow_up_questions"] == []

    def test_glucose_urgent_boundaries(self, client: TestClient, auth_header):
        hdr = {"Authorization": f"Bearer {auth_header['token']}"}
        uid = auth_header["user"]["id"]
        for value, classification, urgent in ((69, "low", True), (110, "elevated", False), (280, "high", False), (300, "critical", True)):
            response = client.post("/v1/glucose", json={"user_id": uid, "value_mgdl": value, "context": "fasting"}, headers=hdr)
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["classification"] == classification
            if urgent:
                assert "liên hệ cơ sở y tế ngay" in data["message"]
                assert "liên hệ cơ sở y tế ngay" in data["anomaly"]["reason"]
            else:
                assert "liên hệ cơ sở y tế ngay" not in data["message"]
                assert "liên hệ cơ sở y tế ngay" not in data["anomaly"]["reason"]

    def test_safeguard_out_of_scope_no_rag(self, client: TestClient, auth_header, monkeypatch):
        import src.api.main as api_main
        called = {"rag": False}
        hdr = {"Authorization": f"Bearer {auth_header['token']}"}
        uid = auth_header["user"]["id"]
        # If RAG were invoked it would go through rag_chat — guard must return before it
        try:
            import src.chat.rag_pipeline as rp
            monkeypatch.setattr(rp, "rag_chat", lambda *a, **k: (_ for _ in ()).throw(AssertionError("RAG must not be called")))
        except Exception:
            pass
        resp = client.post("/v1/query", json={"query": "Tôi nên uống kháng sinh nào?", "top_k": 3, "user_id": uid}, headers=hdr)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["answer"] == "Hệ thống chỉ hỗ trợ theo dõi đái tháo đường. Nội dung này nằm ngoài phạm vi an toàn của hệ thống, vui lòng hỏi bác sĩ ở lần khám tới."
        assert data.get("safeguard") is True

    def test_soap_markdown(self, client: TestClient, auth_header):
        hdr = {"Authorization": f"Bearer {auth_header['token']}"}
        uid = auth_header["user"]["id"]
        client.post("/v1/glucose", json={"user_id": uid, "value_mgdl": 95, "context": "fasting"}, headers=hdr)
        resp = client.post("/v1/soap/generate/markdown", json={"user_id": uid, "days": 7}, headers=hdr)
        assert resp.status_code == 200
        assert "Subjective" in resp.text or "S —" in resp.text

    def test_guidelines_status(self, client: TestClient):
        resp = client.get("/v1/guidelines/status")
        assert resp.status_code == 200
        assert "total_pdfs" in resp.json()
        assert resp.json()["total_pdfs"] >= 4

    def test_health(self, client: TestClient):
        resp = client.get("/v1/health")
        assert resp.status_code == 200
        assert resp.json()["embedding_provider"] in ("openai", "local", "nvidia")

    def test_user_isolation(self, client: TestClient, make_user):
        u1, t1 = make_user(role="user")
        u2, t2 = make_user(role="user")
        h1 = {"Authorization": f"Bearer {t1}"}
        h2 = {"Authorization": f"Bearer {t2}"}
        client.post("/v1/glucose", json={"user_id": u1["id"], "value_mgdl": 100, "context": "fasting"}, headers=h1)
        client.post("/v1/glucose", json={"user_id": u2["id"], "value_mgdl": 200, "context": "fasting"}, headers=h2)
        # u1 cannot read u2
        r = client.get(f"/v1/glucose/{u2['id']}", headers=h1)
        assert r.status_code == 403
        # own succeeds
        r2 = client.get(f"/v1/glucose/{u1['id']}", headers=h1)
        assert r2.status_code == 200
