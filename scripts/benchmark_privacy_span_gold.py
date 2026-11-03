"""Measure FN/FP by reviewed Vietnamese name/address category; emits metrics only."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from src.shared.privacy import PrivacyError, POLICY_VERSION, redact_text

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "evaluation" / "privacy_span_gold_vi.json"


def main() -> int:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    metrics = defaultdict(lambda: {"positive": 0, "negative": 0, "fn": 0, "fp": 0})
    for case in data["cases"]:
        category, text, span = case["category"], case["text"], case["span"]
        detected = False
        try:
            result = redact_text(text)
            detected = result != text or (span is not None and span not in result)
        except PrivacyError:
            detected = True
        bucket = metrics[category]
        if span is None:
            bucket["negative"] += 1
            bucket["fp"] += int(detected)
        else:
            bucket["positive"] += 1
            bucket["fn"] += int(not detected)
    total_fn = sum(row["fn"] for row in metrics.values())
    total_fp = sum(row["fp"] for row in metrics.values())
    report = {"status": "PASSED" if not total_fn and not total_fp else "FAILED",
              "dataset_version": data["version"], "policy_version": POLICY_VERSION,
              "manual_review": data["review"], "metrics": dict(metrics),
              "false_negative": total_fn, "false_positive": total_fp,
              "contains_source_text": False}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
