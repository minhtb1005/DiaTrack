"""Retrieval-only benchmark for the clean NVIDIA index."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_ROOT = ROOT / "embeddings" / "pdf_db_nvidia_verified_20261102_v2"
DATASET = ROOT / "data" / "evaluation" / "diabetes_retrieval_evaluation.json"
ALLOWED = {
    "who_classification_diabetes_2019", "who_hearts_d_diabetes_2020",
    "who_pen_2020_ncd", "byt_qd3319_hd_chandoan_dtd_type2_2017",
    "ada_standards_of_care_2024_abridged", "byt_qd5481_hd_chandoan_dtd_type2_2020",
}
FILE_TO_SOURCE = {
    "WHO_Classification_Diabetes_2019.pdf": "who_classification_diabetes_2019",
    "WHO_HEARTS_D_Diabetes_2020.pdf": "who_hearts_d_diabetes_2020",
    "WHO_PEN_2020_NCD.pdf": "who_pen_2020_ncd",
    "BYT_QD3319_HD_ChanDoan_DTD_Type2_2017.pdf": "byt_qd3319_hd_chandoan_dtd_type2_2017",
    "ADA_Standards_of_Care_2024_Abridged.pdf": "ada_standards_of_care_2024_abridged",
}


def main() -> int:
    os.environ["NVIDIA_PDF_DB_DIR"] = str(INDEX_ROOT)
    from src.chat.retriever import load_vectorstores
    from src.diabetes.scope_guard import is_out_of_scope

    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    eligible, excluded = [], []
    for row in dataset:
        gold = {FILE_TO_SOURCE[name] for name in row["relevant_documents"] if name in FILE_TO_SOURCE}
        (eligible if gold else excluded).append((row, gold))
    hits, reciprocal, source_violations, misses = 0, [], set(), []
    retriever = load_vectorstores().as_retriever(search_kwargs={"k": 5})
    for row, gold in eligible:
        docs = retriever.invoke(row["question"])
        sources = [doc.metadata.get("source_id") for doc in docs]
        source_violations.update(source for source in sources if source not in ALLOWED)
        ranks = [index + 1 for index, source in enumerate(sources) if source in gold]
        hits += bool(ranks)
        reciprocal.append(1 / min(ranks) if ranks else 0)
        if not ranks:
            misses.append({"question_id": row["question_id"], "gold": sorted(gold),
                           "retrieved": sources})
    report = {
        "status": "PASSED" if hits / len(eligible) >= 0.9 and not source_violations else "FAILED",
        "dataset_cases": len(dataset), "eligible_cases": len(eligible),
        "excluded_cases": len(excluded), "excluded_reason": "gold source is not binary-verified",
        "hit_at_5": hits / len(eligible), "mrr_at_5": sum(reciprocal) / len(reciprocal),
        "source_violations": sorted(source_violations), "provider_calls": len(eligible),
        "misses": misses,
        "out_of_scope_guard": {
            question: is_out_of_scope(question) for question in (
                "Điều trị hen phế quản như thế nào?",
                "Phác đồ COPD hiện nay là gì?",
                "Tôi cần tư vấn điều trị trầm cảm.",
            )
        },
    }
    if not all(report["out_of_scope_guard"].values()):
        report["status"] = "FAILED"
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
