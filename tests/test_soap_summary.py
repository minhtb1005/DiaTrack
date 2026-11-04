"""Unit tests for Track B — soap_summary (diabetes pre-visit)."""

import logging
from types import SimpleNamespace

import pytest
from src.diabetes.soap_summary import generate_soap, soap_to_markdown
from src.diabetes.glucose_tracker import add_log


@pytest.fixture(autouse=True)
def isolated_glucose(tmp_path, monkeypatch):
    from src.diabetes import glucose_tracker
    monkeypatch.setattr(glucose_tracker, "GLUCOSE_DB_PATH", tmp_path / "glucose.db")
    glucose_tracker.init_glucose_db()
    from types import SimpleNamespace
    from src.diabetes import soap_summary
    monkeypatch.setattr(soap_summary, "get_long_term_memory", lambda owner: SimpleNamespace(get_user_profile=lambda: {}))


class TestSoapSummary:
    def test_rule_based_fallback_no_openai(self, temp_user, mock_openai, caplog):
        add_log(temp_user, 130, context="fasting")
        add_log(temp_user, 180, context="post_meal_2h")
        with caplog.at_level(logging.WARNING, logger="src.diabetes.soap_summary"):
            data = generate_soap(temp_user, days=14, language="vi")
        assert "soap" in data
        for key in ("subjective", "objective", "assessment"):
            assert key in data["soap"]
            assert isinstance(data["soap"][key], str)
            assert len(data["soap"][key]) > 0
        # P is ALWAYS empty — the doctor decides (placeholder rendered by UI)
        assert data["soap"]["plan"] == ""
        assert "soap_generation mode=fallback reason=RuntimeError" in caplog.text

    def test_logs_llm_mode_without_payload(self, temp_user, monkeypatch, caplog):
        from src.diabetes import soap_summary
        from src.shared import nvidia

        add_log(temp_user, 130, context="fasting")
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=(
            '{"subjective":"S","objective":"O","assessment":"A","plan":""}'
        )), finish_reason="stop")])
        request = {}
        def create(**kwargs):
            request.update(kwargs)
            return response
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        monkeypatch.setattr(nvidia, "llm_client", lambda: client)
        monkeypatch.setenv("NVIDIA_CHAT_MODEL_LIGHT", "test-light-model")

        with caplog.at_level(logging.INFO, logger="src.diabetes.soap_summary"):
            data = soap_summary.generate_soap(temp_user, days=7)

        assert data.get("_fallback_reason") is None
        assert "soap_generation mode=llm" in caplog.text
        assert request["model"] == "test-light-model"
        assert request["max_tokens"] == 2048
        assert request["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
        assert temp_user not in caplog.text
        assert "130" not in caplog.text

    def test_empty_llm_content_falls_back_with_finish_reason(self, temp_user, monkeypatch, caplog):
        from src.diabetes import soap_summary
        from src.shared import nvidia

        response = SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=None), finish_reason="length"
        )])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: response)))
        monkeypatch.setattr(nvidia, "llm_client", lambda: client)

        with caplog.at_level(logging.WARNING, logger="src.diabetes.soap_summary"):
            data = soap_summary.generate_soap(temp_user, days=7)

        assert data["_fallback_reason"] == "RuntimeError"
        assert "soap_generation empty_content finish_reason=length" in caplog.text

    def test_soap_audit_links_and_hba1c(self, temp_user, mock_openai):
        add_log(temp_user, 130, context="fasting", notes="khát nước nhiều")
        add_log(temp_user, 180, context="post_meal_2h")
        data = generate_soap(temp_user, days=14, language="vi")
        assert "HbA1c" in data["soap"]["assessment"]
        assert "[Xem log #" in data["soap"]["subjective"]
        assert "[Xem log #" in data["soap"]["objective"]
        assert "[Xem log #" in data["soap"]["assessment"]
        assert data["soap"]["plan"] == ""

    def test_soap_does_not_impose_unapproved_measurement_kpi(self, temp_user, mock_openai):
        add_log(temp_user, 95, context="fasting")
        data = generate_soap(temp_user, days=7, language="vi")
        assert "KPI" not in data["soap"]["subjective"]
        assert "không thể kết luận đạt hay chưa đạt" in data["soap"]["assessment"]

    def test_soap_no_logs(self, temp_user, mock_openai):
        data = generate_soap(temp_user, days=14, language="vi")
        assert data["stats"]["total_logs"] == 0
        assert "Chưa có" in data["soap"]["subjective"] or "Chưa có" in data["soap"]["objective"] or "No" in data["soap"]["objective"]

    def test_markdown_format(self, temp_user, mock_openai):
        add_log(temp_user, 110, context="fasting")
        data = generate_soap(temp_user, days=7, language="vi")
        md = soap_to_markdown(data)
        assert "# Tóm tắt trước tái khám" in md
        assert "## S — Subjective" in md
        assert "## O — Objective" in md
        assert "## A — Assessment" in md
        assert "## P — Plan" in md
        assert "không thay thế" in md

    def test_period_field(self, temp_user, mock_openai):
        add_log(temp_user, 100, context="random")
        data = generate_soap(temp_user, days=30, language="vi")
        assert data["period"] == "30 ngày"

    def test_transcript_draft_marks_missing_and_keeps_plan_empty(self, client, make_user):
        patient, token = make_user()
        response = client.post(
            "/v1/soap/drafts",
            json={"patient_id": patient["id"], "transcript": "Tôi thấy khát nước."},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["plan"] == ""
        assert data["objective"] == "chưa ghi nhận"
        assert "chỉ số đường huyết" in data["missing"]
        assert data["subjective"].endswith("[Transcript]")
        assert "không phải chẩn đoán" in data["assessment"]
