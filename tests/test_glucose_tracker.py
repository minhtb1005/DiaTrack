"""Unit tests for Track A — glucose_tracker (diabetes spec)."""

import pytest
from tests._helpers import make_crud_case, assert_classify_first
from src.diabetes.glucose_tracker import (
    classify_glucose,
    should_escalate_to_doctor,
    add_log,
    get_stats,
    get_logs,
)


class TestClassifyGlucose:
    @pytest.mark.parametrize("context", ["fasting", "post_meal_2h", "random"])
    @pytest.mark.parametrize("value", [85, 99, 100, 110, 125, 126, 130, 140, 180, 199, 200, 210, 250])
    def test_non_alert_value_has_no_diagnostic_band(self, value, context):
        cls, message = classify_glucose(value, context)
        assert cls == "no_alert"
        assert "không xác nhận" in message

    def test_raised_alert_is_context_independent(self):
        for context in ("fasting", "post_meal_2h", "random"):
            cls, message = classify_glucose(251, context)
            assert cls == "alert_high"
            assert "liên hệ bác sĩ" in message

    def test_hypoglycemia(self):
        cls, msg = classify_glucose(65, "random")
        assert cls == "low"
        assert "dưới 70" in msg and "liên hệ cơ sở y tế" in msg

    def test_critical_high(self):
        cls, _ = classify_glucose(350, "random")
        assert cls == "critical"

    def test_no_legacy_band_labels(self):
        assert {classify_glucose(v, "random")[0] for v in (70, 139, 150, 200, 250)} == {"no_alert"}


class TestGlucoseStatsAndEscalation:
    def test_add_and_stats(self, temp_user):
        add_log(temp_user, 95, context="fasting")
        add_log(temp_user, 110, context="fasting")
        add_log(temp_user, 210, context="post_meal_2h")
        stats = get_stats(temp_user)
        assert stats["total_logs"] == 3
        assert stats["avg_mgdl"] == pytest.approx(138.3, rel=1e-2)
        assert stats["classification_counts"] == {"no_alert": 3}

    def test_logs_per_week_kpi(self, temp_user):
        # 1 log → <3/week should be flagged in stats
        add_log(temp_user, 100, context="fasting")
        stats = get_stats(temp_user)
        assert stats["logs_per_week"] < 3

    def test_escalation_critical(self, temp_user):
        add_log(temp_user, 350, context="random")
        assert should_escalate_to_doctor(temp_user) is True

    def test_legacy_high_band_does_not_escalate(self, temp_user):
        for _ in range(3):
            add_log(temp_user, 180, context="fasting")
        assert should_escalate_to_doctor(temp_user) is False

    def test_post_meal_message_does_not_apply_ogtt_diagnosis(self):
        _, message = classify_glucose(210, "post_meal_2h")
        assert "không xác nhận" in message

    def test_no_escalation_when_no_alert(self, temp_user):
        add_log(temp_user, 90, context="fasting")
        add_log(temp_user, 95, context="fasting")
        assert should_escalate_to_doctor(temp_user) is False

    def test_get_logs_limit(self, temp_user):
        for i in range(5):
            add_log(temp_user, 90 + i, context="random")
        logs = get_logs(temp_user, limit=2)
        assert len(logs) == 2

    def test_historical_stored_label_is_reclassified_on_read(self, temp_user):
        import src.diabetes.glucose_tracker as tracker
        import sqlite3
        rec = add_log(temp_user, 110, context="fasting")
        with sqlite3.connect(tracker.GLUCOSE_DB_PATH) as conn:
            conn.execute("UPDATE glucose_logs SET classification = 'elevated' WHERE id = ?", (rec["id"],))
        assert get_logs(temp_user, limit=1)[0]["classification"] == "no_alert"
        assert get_stats(temp_user)["classification_counts"] == {"no_alert": 1}


@pytest.mark.parametrize("args,expected", [
    make_crud_case((85, "fasting"), "no_alert"),
    make_crud_case((130, "fasting"), "no_alert"),
    make_crud_case((65, "random"), "low"),
    make_crud_case((350, "random"), "critical"),
])
def test_classify_via_helpers(args, expected):
    assert_classify_first(classify_glucose, args, expected)


def test_single_reading_message_does_not_diagnose():
    for value, context in ((110, "fasting"), (130, "fasting"), (190, "post_meal_2h")):
        _, message = classify_glucose(value, context)
        assert "chẩn đoán" not in message.lower()
        assert "tiền đái tháo đường" not in message.lower()
        assert "tiền đtđ" not in message.lower()
        assert "đổi liều" not in message.lower()
