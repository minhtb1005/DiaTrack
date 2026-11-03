def test_stream_hides_draft_when_review_is_pending():
    from src.chat.router import _review_safe_events

    events = [
        {"event": "token", "data": {"delta": "DRAFT_SECRET"}},
        {
            "event": "done",
            "data": {
                "answer": "DRAFT_SECRET",
                "formatted_answer": "DRAFT_SECRET",
                "status": "pending_review",
                "review_id": "review-1",
                "evaluation": {"raw": "DRAFT_SECRET"},
            },
        },
    ]

    output = "".join(_review_safe_events(events))
    assert "DRAFT_SECRET" not in output
    assert "pending_review" in output
    assert "đang chờ bác sĩ duyệt" in output


def test_stream_request_requiring_review_uses_guarded_query(monkeypatch):
    import src.chat.router as router
    from src.chat.schemas import QueryRequest

    called = []
    monkeypatch.setattr(router, "_scope_answer", lambda *args: None)
    monkeypatch.setattr(
        router,
        "rag_query",
        lambda req, user: called.append(req.require_doctor_review) or {
            "answer": "Đang chờ duyệt",
            "status": "pending_review",
        },
    )

    response = router.rag_query_stream(
        QueryRequest(query="Theo dõi đường huyết", require_doctor_review=True),
        current_user={"id": "patient-1", "role": "user", "username": "patient"},
    )

    assert response.media_type == "text/event-stream"
    assert called == [True]


def test_default_secret_key_is_rejected(monkeypatch):
    import src.shared.config as config

    monkeypatch.setattr(config, "SECRET_KEY", config.DEFAULT_SECRET_KEY)
    try:
        config.validate_secret_key()
    except RuntimeError as exc:
        assert "SECRET_KEY" in str(exc)
    else:
        raise AssertionError("default SECRET_KEY was accepted")


def test_admin_router_import_does_not_load_chunking_models(monkeypatch):
    import importlib
    import sys

    import src.admin as admin
    previous = getattr(admin, "tracing_router", None)
    with monkeypatch.context() as isolated:
        isolated.delitem(sys.modules, "src.admin.tracing_router", raising=False)
        isolated.delitem(sys.modules, "src.shared.chunk_strategies", raising=False)
        importlib.import_module("src.admin.tracing_router")
        assert "src.shared.chunk_strategies" not in sys.modules
    if previous is not None:
        admin.tracing_router = previous


def test_reranker_loads_lazily_and_only_from_local_cache(monkeypatch):
    import src.chat.generator as generator

    calls = []
    monkeypatch.setattr(generator, "_CROSS_ENCODER_AVAILABLE", True)
    monkeypatch.setattr(
        generator,
        "CrossEncoder",
        lambda model, **kwargs: calls.append((model, kwargs)) or object(),
    )
    generator._get_reranker.cache_clear()

    assert calls == []
    generator._get_reranker()
    generator._get_reranker()
    assert calls == [(generator.RERANKER_MODEL, {"local_files_only": True})]


def test_triage_red_flag_failure_returns_safety_warning(monkeypatch):
    from src.triage.router import triage_endpoint
    from src.triage.schemas import TriageRequest

    def fail_red_flag_check(message):
        raise RuntimeError("detector unavailable")

    monkeypatch.setattr("src.triage.red_flag.check_red_flag", fail_red_flag_check)
    response = triage_endpoint(TriageRequest(message="Tôi thấy không khỏe"), current_user=None)

    assert response.emergency is True
    assert response.red_flag_type == "safety_check_unavailable"
    assert "115" in response.message


def test_mandatory_review_does_not_depend_on_ai_judge(client, auth_header, monkeypatch):
    import src.chat.router as router
    import src.chat.rag_pipeline as pipeline
    from src.reviews.service import get_review

    def fail_judge(*args):
        raise AssertionError("Mandatory review must go directly to the clinician")

    monkeypatch.setattr(router, "evaluate_rag", fail_judge)
    monkeypatch.setattr(pipeline, "rag_chat", lambda *args, **kwargs: {
        "raw_answer": {"answer": "PRIVATE_DRAFT", "cited_sources": []}, "contexts": [],
    })
    response = client.post("/v1/query", headers={"Authorization": f"Bearer {auth_header['token']}"}, json={
        "query": "Theo dõi đường huyết ở người đái tháo đường týp 2", "require_doctor_review": True,
    })
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "pending_review"
    assert "PRIVATE_DRAFT" not in response.text
    review = get_review(response.json()["review_id"])
    assert review["draft_answer"] == "PRIVATE_DRAFT"
    assert review["routed_role"] == "doctor"
    assert review["evaluation"]["review_required_by_workflow"] is True
