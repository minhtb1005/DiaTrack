"""Single source for glucose thresholds and alert classification.

`scope_rules` is the product authority, not a clinical guideline citation.
Legacy display bands lack a verified clinical source and must not be used to
diagnose diabetes. Values are in mg/dL.
"""
from __future__ import annotations

from dataclasses import dataclass

SCOPE_SOURCE = "docs/project_requirements.json#scope_rules"
LEGACY_SOURCE = "legacy demo value; clinical source unverified"

@dataclass(frozen=True)
class Threshold:
    value: float
    source: str


THRESHOLDS = {
    "hypoglycemia": Threshold(70, SCOPE_SOURCE),
    "fasting_diabetes": Threshold(126, SCOPE_SOURCE),
    "postprandial_diabetes": Threshold(200, SCOPE_SOURCE),
    "spike_high": Threshold(250, SCOPE_SOURCE),
    "critical_high": Threshold(300, SCOPE_SOURCE),
    "fasting_normal_max": Threshold(100, LEGACY_SOURCE),
    "fasting_prediabetes_max": Threshold(125, LEGACY_SOURCE),
    "postprandial_normal_max": Threshold(140, LEGACY_SOURCE),
    "postprandial_prediabetes_max": Threshold(199, LEGACY_SOURCE),
    "random_normal_max": Threshold(140, LEGACY_SOURCE),
    "random_elevated_max": Threshold(200, LEGACY_SOURCE),
}


def glucose_severity(value_mgdl: float, context: str = "random") -> str:
    """Return low, normal, elevated, high, or critical; never a diagnosis."""
    v = float(value_mgdl)
    if v < THRESHOLDS["hypoglycemia"].value:
        return "low"
    if v >= THRESHOLDS["critical_high"].value:
        return "critical"
    if context == "fasting":
        if v < THRESHOLDS["fasting_normal_max"].value:
            return "normal"
        if v <= THRESHOLDS["fasting_prediabetes_max"].value:
            return "elevated"
        return "high"
    if context == "post_meal_2h":
        if v < THRESHOLDS["postprandial_normal_max"].value:
            return "normal"
        if v <= THRESHOLDS["postprandial_prediabetes_max"].value:
            return "elevated"
        return "high"
    if v < THRESHOLDS["random_normal_max"].value:
        return "normal"
    if v < THRESHOLDS["random_elevated_max"].value:
        return "elevated"
    return "high"


def spike_direction(value_mgdl: float) -> str | None:
    if value_mgdl < THRESHOLDS["hypoglycemia"].value:
        return "low"
    if value_mgdl > THRESHOLDS["spike_high"].value:
        return "high"
    return None
