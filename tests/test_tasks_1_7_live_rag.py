"""Live NVIDIA RAG and clinician review against disposable SQLite stores."""

import sqlite3
import pytest


pytestmark = pytest.mark.live_provider


def test_live_trend_review_roundtrip(client, make_user, doctor_user, monkeypatch, tmp_path):
    from src.auth import db as auth_db
    from src.chat import retriever
    from src.chat import rag_pipeline
    from src.shared.nvidia import get_nvidia_keys

    assert get_nvidia_keys(), "NVIDIA credentials are required for this live test"
    # Keep every retrieved context synthetic; no project corpus or patient record
    # may be sent to the external LLM in this test.
    index_path = tmp_path / "synthetic_nvidia_index"
    monkeypatch.setattr(retriever, "_resolve_db_dir", lambda _strategy: str(index_path))
    monkeypatch.setitem(rag_pipeline.retrieve_context.__globals__,
                        "_resolve_db_dir", lambda _strategy: str(index_path))
    synthetic_source = "TEST_ONLY_SYNTHETIC_DIABETES_GUIDANCE"
    store = retriever.load_vectorstores()
    store.add_texts(
        ["Dữ liệu thử tổng hợp: hai số đo đường huyết tại nhà không đủ để kết luận đạt mục tiêu cá nhân. Hãy trao đổi mục tiêu với bác sĩ."],
        metadatas=[{"source_id": synthetic_source, "file_name": "synthetic-test.txt", "page_numbers": "1"}],
    )
    assert {d.metadata["source_id"] for d in retriever.cached_documents()} == {synthetic_source}
    patient, token = make_user()
    _, other_token = make_user()
    headers = {"Authorization": f"Bearer {token}"}
    question = (
        "Tôi mắc đái tháo đường týp 2; các số đo tại nhà là 110 và 120 mg/dL. "
        "Hãy giải thích xu hướng, trích nguồn và nhắc rằng mục tiêu cá nhân do bác sĩ xác định."
    )
    # The app can import retriever under either package name. Check the exact
    # function bound into the pipeline before any generation/evaluation call.
    preflight = rag_pipeline.maybe_inject_gho_stats(
        question, rag_pipeline.retrieve_context(question, top_k=5))
    assert preflight and {c.source_id for c in preflight} == {synthetic_source}
    def allow_test_source_only(contexts):
        assert contexts and {c.source_id for c in contexts} == {synthetic_source}
    import src.shared.corpus_provenance as provenance
    monkeypatch.setattr(provenance, "validate_context_provenance", allow_test_source_only)
    monkeypatch.setattr(rag_pipeline, "validate_context_provenance", allow_test_source_only)
    response = client.post("/v1/query", headers=headers, json={
        "query": question, "language": "vi", "require_doctor_review": True,
    })
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "pending_review"
    assert result["review_id"]
    assert result["contexts"] and all(c.get("source_id") == synthetic_source for c in result["contexts"])
    assert "chờ bác sĩ duyệt" in result["answer"]
    review_id = result["review_id"]

    with sqlite3.connect(auth_db.AUTH_DB_PATH) as db:
        row = db.execute(
            "SELECT status, requester_id, draft_answer FROM review_requests WHERE id=?",
            (review_id,),
        ).fetchone()
    assert row and row[0] == "pending" and row[1] == patient["id"] and row[2]
    assert row[2] != result["answer"]

    mine = client.get(f"/v1/reviews/{review_id}", headers=headers)
    assert mine.status_code == 200
    assert "draft_answer" not in mine.json()
    assert client.get(f"/v1/reviews/{review_id}", headers={"Authorization": f"Bearer {other_token}"}).status_code == 403
    assert client.post(f"/v1/reviews/{review_id}/decide", headers=headers,
                       json={"decision": "approved"}).status_code == 403

    doctor_headers = {"Authorization": f"Bearer {doctor_user['token']}"}
    pending = client.get("/v1/reviews?status=pending", headers=doctor_headers)
    assert pending.status_code == 200
    assert any(r["id"] == review_id for r in pending.json()["reviews"])
    final_answer = "Hai số đo chưa đủ để kết luận; hãy trao đổi mục tiêu cá nhân với bác sĩ."
    decided = client.post(f"/v1/reviews/{review_id}/decide", headers=doctor_headers,
                          json={"decision": "revised", "final_answer": final_answer})
    assert decided.status_code == 200, decided.text
    visible = client.get(f"/v1/reviews/{review_id}", headers=headers)
    assert visible.status_code == 200
    assert visible.json()["status"] == "revised"
    assert visible.json()["final_answer"] == final_answer
