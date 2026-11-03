"""One synthetic live smoke; records the exact sanitized provider payload locally."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.chat.generator import generate_answer
from src.chat.retriever import retrieve_context
from src.shared import nvidia
from src.shared.corpus_provenance import validate_context_provenance
from src.shared.models.llm_io import LLMInput
from src.shared.privacy import sanitize, sanitize_chat

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "test-results" / "verified-live-smoke-payload.json"
QUESTION = "Theo WHO, ngưỡng đường huyết lúc đói để chẩn đoán đái tháo đường là bao nhiêu?"


def main() -> int:
    captured = {"embedding": [], "chat": []}
    original_embed = nvidia.embed_texts
    original_once = nvidia._CompletionsNS._once

    def capture_embed(texts, model, mode="passage"):
        safe = sanitize(texts)
        captured["embedding"].append({"model": model, "mode": mode, "input": safe})
        return original_embed(texts, model, mode)

    def capture_chat(self, key, model, kwargs):
        safe = sanitize_chat(dict(kwargs, model=model))
        captured["chat"].append(safe)
        return original_once(self, key, model, kwargs)

    nvidia.embed_texts = capture_embed
    nvidia._CompletionsNS._once = capture_chat
    try:
        contexts = retrieve_context(QUESTION, top_k=5)[:3]
        validate_context_provenance(contexts)
        llm_input = LLMInput(query=QUESTION, language="vi", contexts=[c.model_dump() for c in contexts])
        output = generate_answer(llm_input)
    finally:
        nvidia.embed_texts = original_embed
        nvidia._CompletionsNS._once = original_once

    report = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "synthetic_only": True,
        "source_ids": [context.source_id for context in contexts],
        "provenance_validated": True,
        "sanitized_outbound_payload": captured,
        "answer_received": bool(output.answer),
        "cited_sources": output.cited_sources,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "timestamp", "synthetic_only", "source_ids", "provenance_validated",
        "answer_received", "cited_sources")}, ensure_ascii=True, indent=2))
    return 0 if report["answer_received"] and report["provenance_validated"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
