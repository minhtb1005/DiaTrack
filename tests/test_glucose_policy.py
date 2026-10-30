"""Cross-module glucose boundaries and provenance."""
from src.shared.glucose_policy import THRESHOLDS, glucose_severity, spike_direction
from src.diabetes.glucose_tracker import classify_glucose
from src.diabetes.anomaly_detector import detect_spike
from src.labs.lab_thresholds import is_panic


def test_threshold_provenance_is_explicit():
    assert all(item.source for item in THRESHOLDS.values())
    assert THRESHOLDS["critical_high"].source == "docs/project_requirements.json#scope_rules"
    assert "unverified" in THRESHOLDS["random_normal_max"].source


def test_shared_boundaries_across_modules():
    for value, severity, spike, panic in (
        (69, "low", "spike_low", True),
        (70, "normal", "none", False),
        (250, "high", "none", False),
        (251, "high", "spike_high", False),
        (299, "high", "spike_high", False),
        (300, "critical", "spike_high", True),
    ):
        assert glucose_severity(value, "fasting") == severity
        assert classify_glucose(value, "fasting")[0] == severity
        assert detect_spike(value)["type"] == spike
        assert is_panic("1558-6", value) == panic


def test_ldl_250_is_independent_of_glucose():
    assert is_panic("18262-6", 251)
    assert not is_panic("18262-6", 250)
    assert spike_direction(250) is None
