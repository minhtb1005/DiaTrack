"""Live NVIDIA smoke test for triage NLU. Uses synthetic text only."""
from __future__ import annotations

import json
import time

from src.shared.nvidia import get_nvidia_keys
from src.triage.triage_nlu import _parse_llm


def main() -> int:
    if not get_nvidia_keys():
        print(json.dumps({"status": "FAILED", "reason": "missing_nvidia_key"}))
        return 1
    prompts = [
        "khát nhiều, tiểu nhiều, muốn khám tuần sau trừ T4",
        "Tê rần 10 đầu ngón chân, mắt mờ 2 hôm",
    ]
    started = time.perf_counter()
    results = [_parse_llm(prompt) for prompt in prompts]
    expected = [
        lambda r: ({s["code"] for s in r["symptoms"]} >= {"hyperglycemia"}
                   and "booking" in r["intents"]
                   and "Wednesday" in r["time_constraints"]["excluded_weekdays"]),
        lambda r: ({s["code"] for s in r["symptoms"]} >= {"neuropathy", "retinopathy"}
                   and r["specialty"] == "Endocrinology_Complication"),
    ]
    passed = [bool(result and check(result)) for result, check in zip(results, expected)]
    status = "PASSED" if all(passed) else "FAILED"
    print(json.dumps({
        "status": status,
        "elapsed_s": round(time.perf_counter() - started, 2),
        "passed": passed,
        "results": results,
    }, ensure_ascii=False))
    return 0 if status == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
