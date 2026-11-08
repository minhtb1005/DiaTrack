"""Benchmark one local/Hugging Face STT model on a pinned public VietMed sample."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def normalize(text: str) -> list[str]:
    text = "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", text.replace("đ", "d"))


def edit_distance(left: list[str], right: list[str]) -> int:
    row = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        nxt = [i]
        for j, b in enumerate(right, 1):
            nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (a != b)))
        row = nxt
    return row[-1]


def metric(reference: str, prediction: str) -> tuple[float, float]:
    ref_words, pred_words = normalize(reference), normalize(prediction)
    ref_chars, pred_chars = list("".join(ref_words)), list("".join(pred_words))
    return (
        edit_distance(ref_words, pred_words) / max(1, len(ref_words)),
        edit_distance(ref_chars, pred_chars) / max(1, len(ref_chars)),
    )


def region(value: object) -> str:
    text = str(value or "unknown").strip().lower()
    if text in {"north", "northern", "bac", "bắc"}:
        return "north"
    if text in {"central", "trung", "trung bộ", "north central coast", "south central coast", "central highland"}:
        return "central"
    if text in {"south", "southern", "nam", "miền nam", "south east", "south west"}:
        return "south"
    return "unknown"


def audio_bytes(value: object) -> bytes:
    if not isinstance(value, dict):
        raise ValueError("audio column is not a mapping")
    if value.get("bytes"):
        return value["bytes"]
    if value.get("path"):
        return Path(value["path"]).read_bytes()
    raise ValueError("audio row has neither bytes nor path")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", default="leduckhai/VietMed")
    parser.add_argument("--revision", default="main")
    parser.add_argument("--split", default="test")
    parser.add_argument("--per-region", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    from datasets import Audio, load_dataset
    from huggingface_hub import HfApi
    from transformers import pipeline

    dataset_info = HfApi().dataset_info(args.dataset, revision=args.revision)
    model_info = HfApi().model_info(args.model)
    stream = load_dataset(args.dataset, split=args.split, revision=dataset_info.sha, streaming=True)
    stream = stream.cast_column("audio", Audio(decode=False))
    quotas = {"north": args.per_region, "central": args.per_region, "south": args.per_region}
    selected = []
    for item in stream:
        accent = region(item.get("accent"))
        if quotas.get(accent, 0) <= 0:
            continue
        text = str(item.get("sentence") or item.get("transcription") or item.get("text") or "").strip()
        if not text:
            continue
        selected.append((accent, text, audio_bytes(item["audio"]), str(item.get("speaker_id") or item.get("speaker") or "unknown")))
        quotas[accent] -= 1
        if not any(quotas.values()):
            break
    if any(quotas.values()):
        raise RuntimeError(f"insufficient region rows: {quotas}")

    recognizer = pipeline("automatic-speech-recognition", model=args.model, device=-1)
    rows = []
    for accent, reference, audio, speaker in selected:
        started = time.perf_counter()
        result = recognizer(audio, generate_kwargs={"language": "vi", "task": "transcribe"})
        latency = time.perf_counter() - started
        prediction = str(result.get("text", "")).strip()
        wer, cer = metric(reference, prediction)
        rows.append({
            "region": accent,
            "speaker_hash": hashlib.sha256(speaker.encode()).hexdigest()[:12],
            "reference": reference,
            "prediction": prediction,
            "wer": wer,
            "cer": cer,
            "latency_s": latency,
        })

    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in rows:
        grouped[item["region"]].append(item)
    summary = {
        "dataset": args.dataset,
        "dataset_revision": dataset_info.sha,
        "model": args.model,
        "model_revision": model_info.sha,
        "split": args.split,
        "samples": len(rows),
        "mean_wer": sum(x["wer"] for x in rows) / len(rows),
        "mean_cer": sum(x["cer"] for x in rows) / len(rows),
        "mean_latency_s": sum(x["latency_s"] for x in rows) / len(rows),
        "by_region": {
            key: {
                "samples": len(items),
                "mean_wer": sum(x["wer"] for x in items) / len(items),
                "mean_cer": sum(x["cer"] for x in items) / len(items),
            }
            for key, items in grouped.items()
        },
        "scope": "public general medical ASR benchmark; not a DiaTrack runtime safety gate",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
