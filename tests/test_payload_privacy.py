"""Synthetic HTTP-boundary tests: no provider, corpus or application DB access."""
import json
import socket
from pathlib import Path
from types import SimpleNamespace
from collections import Counter

import httpx
import pytest

from src.shared.privacy import PrivacyError, redact_text, sanitize, sanitize_chat, verified_public_scope
from src.shared.corpus_provenance import validate_context_provenance
from src.shared import nvidia


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("external network forbidden")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(nvidia, "_raise_if_no_keys", lambda: ["synthetic-key-a", "synthetic-key-b"])


@pytest.fixture
def capture(monkeypatch):
    from openai import OpenAI
    original = httpx.Client
    calls = []
    statuses = []

    def handle(request):
        body = json.loads(request.content)
        calls.append(body)
        status = statuses.pop(0) if statuses else 200
        if status != 200:
            return httpx.Response(status, json={"error": {"message": "synthetic failure"}})
        if request.url.path.endswith("embeddings"):
            return httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2]} for _ in body["input"]]})
        if body.get("stream"):
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, content='data: {"id":"test","object":"chat.completion.chunk","created":0,"model":"test","choices":[{"index":0,"delta":{"content":"clinical answer"}}]}\n\ndata: [DONE]\n\n')
        return httpx.Response(200, json={"id": "test", "object": "chat.completion", "created": 0, "model": "test", "choices": [{"index": 0, "message": {"role": "assistant", "content": "clinical answer"}, "finish_reason": "stop"}]})

    transport = httpx.MockTransport(handle)
    class OfflineClient(original):
        def __init__(self, **kw):
            super().__init__(transport=transport, **kw)
    monkeypatch.setattr(httpx, "Client", OfflineClient)
    monkeypatch.setattr("openai.OpenAI", lambda **kw: OpenAI(**kw, max_retries=0, http_client=OfflineClient()))
    return calls, statuses


@pytest.mark.parametrize("raw", ["+84 912 345 678", "0912.345.678", "synthetic@example.invalid", "001 234 567 890", "01/02/1980", "Tôi tên Nguyễn Văn An", "toi ten Nguyen Van An", "BHYT: DN40123456789", "https://example.invalid/patient/token", r"C:\Users\Patient\record.txt"])
def test_required_spans(raw):
    counts = Counter()
    cleaned = redact_text(raw, counts)
    assert raw not in cleaned, "required synthetic span survived"
    assert sum(counts.values()) > 0


@pytest.mark.parametrize("value", [69, 70, 250, 251, 299, 300])
def test_clinical_values_and_negation(value):
    clinical = f"Glucose {value} mg/dL; không khó thở; hôm qua; 7.0 mmol/L"
    assert redact_text(clinical) == clinical


def test_nested_json_and_identity_fields():
    result = sanitize({"name": "Nguyễn Văn An", "arguments": json.dumps({"username": "synthetic-person", "email": "a@example.invalid"}), "metadata": {"address": "synthetic address"}})
    assert "synthetic-person" not in json.dumps(result)
    assert "example.invalid" not in json.dumps(result)
    assert "synthetic address" not in json.dumps(result)


@pytest.mark.parametrize("extra", [{"extra_headers": {"x-patient": "raw"}}, {"extra_body": {"image_url": "raw"}}, {"temperature": "raw"}, {"stream_options": {"patient": "raw"}}])
def test_unsupported_payload_has_zero_requests(capture, extra):
    calls, _ = capture
    with pytest.raises(PrivacyError):
        nvidia.RotatingNvidiaClient().chat.completions.create(model="test", messages=[{"role": "user", "content": "glucose"}], **extra)
    assert not calls


@pytest.mark.parametrize("stream", [False, True])
def test_chat_sources_retry_and_stream(capture, stream):
    calls, statuses = capture
    statuses.append(429)
    sources = ["query", "document", "metadata", "short-term", "episodic", "long-term", "judge-answer", "GHO"]
    messages = [{"role": role, "content": f"{source}: synthetic-{i}@example.invalid; 70 mg/dL"} for i, (source, role) in enumerate(zip(sources, ["system", "user", "assistant", "tool"] * 2))]
    result = nvidia.RotatingNvidiaClient().chat.completions.create(model="test", messages=messages, stream=stream, extra_body={"metadata": {"name": "Synthetic Person"}})
    if stream:
        assert "".join(c.choices[0].delta.content or "" for c in result) == "clinical answer"
    assert len(calls) == 2
    assert all("example.invalid" not in json.dumps(c) and "Synthetic Person" not in json.dumps(c) for c in calls), "synthetic PII crossed HTTP boundary"
    assert all("70 mg/dL" in json.dumps(c) for c in calls)
    assert messages[0]["content"].find("example.invalid") >= 0  # caller data unmodified


@pytest.mark.parametrize("mode", ["query", "passage"])
def test_embedding_boundary(capture, mode):
    calls, statuses = capture
    statuses.append(401)
    assert nvidia.embed_texts(["0912 345 678; 300 mg/dL"], "test", mode) == [[0.1, 0.2]]
    assert len(calls) == 2
    assert all("0912" not in json.dumps(c) and "300 mg/dL" in json.dumps(c) for c in calls)


def test_rotation_log_has_slot_not_key(capture, caplog):
    _, statuses = capture
    statuses.append(401)
    with caplog.at_level("WARNING"):
        nvidia.embed_texts(["70 mg/dL"], "test", "query")
    assert "key_slot=1/2" in caplog.text
    assert "synthetic-key" not in caplog.text


def test_embedding_rotates_past_forbidden_key(capture):
    calls, statuses = capture
    statuses.append(403)
    assert nvidia.embed_texts(["70 mg/dL"], "test", "query") == [[0.1, 0.2]]
    assert len(calls) == 2


def test_uncertain_identity_blocks_without_network(capture):
    calls, _ = capture
    with pytest.raises(PrivacyError):
        nvidia.embed_texts(["địa chỉ: số 12 đường thử"], "test")
    assert not calls


def test_hard_fallback_is_sanitized(capture, monkeypatch):
    calls, statuses = capture
    statuses.extend([503, 503])
    nvidia.RotatingNvidiaClient().chat.completions.create(model=nvidia.hard_model(), messages=[{"role": "user", "content": "a@example.invalid"}])
    assert [c["model"] for c in calls] == [nvidia.hard_model(), nvidia.hard_model(), nvidia.light_model()]
    assert all("example.invalid" not in json.dumps(c) for c in calls)


def test_audit_is_read_only_and_reports_counts(tmp_path):
    import sqlite3
    from scripts.audit_payload_privacy import scan_database
    source = tmp_path / "synthetic.db"
    with sqlite3.connect(source) as conn:
        conn.execute("create table chunks (content text)")
        conn.execute("insert into chunks values (?)", ("synthetic@example.invalid; 70 mg/dL",))
    before = source.read_bytes()
    report = scan_database(source, "synthetic")
    assert source.read_bytes() == before
    assert "synthetic@example.invalid" not in json.dumps(report)
    assert report["findings"][0]["counts"]["email"] == 1


def test_identity_scope_is_request_local():
    from concurrent.futures import ThreadPoolExecutor
    from src.shared.privacy import identity_scope
    def run(owner):
        with identity_scope(owner):
            return redact_text(owner), redact_text("clinical fact")
    with ThreadPoolExecutor() as pool:
        results = list(pool.map(run, ["synthetic-owner-A", "synthetic-owner-B"] * 10))
    assert all(item == ("[REDACTED]", "clinical fact") for item in results)
    assert redact_text("synthetic-owner-A") == "synthetic-owner-A"


def test_memory_owners_and_legacy_quarantine(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace
    from src.shared.memory import short_term, episodic, long_term
    for module, factory, accessor in [(short_term, "ShortTermMemory", "get_short_term_memory"), (episodic, "EpisodicMemory", "get_episodic_memory")]:
        monkeypatch.setattr(module, factory, lambda: SimpleNamespace(messages=[]))
        monkeypatch.setattr(module, "_owner_memories", {})
        monkeypatch.setattr(module, module.__name__.split(".")[-1] + "_memory", SimpleNamespace(messages=["legacy-private"]))
        get = getattr(module, accessor)
        with ThreadPoolExecutor() as pool:
            owners = list(pool.map(get, ["owner-A", "owner-B"] * 20))
        assert all(x is owners[0] for x in owners[::2])
        assert all(x is owners[1] for x in owners[1::2])
        owners[0].messages.append("A-private")
        assert owners[1].messages == []
        assert get() is not get()
    monkeypatch.setattr(long_term, "LongTermMemory", lambda user_id: SimpleNamespace(user_id=user_id))
    with ThreadPoolExecutor() as pool:
        results = list(pool.map(long_term.get_long_term_memory, ["A", "B"] * 20))
    assert [x.user_id for x in results] == ["A", "B"] * 20


def test_api_index_memory_transport_isolation(client, make_user, capture, monkeypatch, tmp_path):
    """Actual API/auth SQLite, Chroma, memory and SDK; only provider transport is replaced."""
    import importlib
    from src.chat import rag_pipeline as pipeline
    from src.shared.memory import episodic, long_term, short_term
    from src.shared.nvidia import NvidiaEmbeddings
    calls, _ = capture
    tokenizer = SimpleNamespace(tokenize=lambda value: value.split())
    monkeypatch.setattr(short_term.AutoTokenizer, "from_pretrained", lambda *args, **kwargs: tokenizer)
    monkeypatch.setattr(episodic.AutoTokenizer, "from_pretrained", lambda *args, **kwargs: tokenizer)
    for key in nvidia._KEY_NAMES:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("NVDIA_API_KEY", "synthetic-only-key")
    # Patch the exact retriever namespace bound by the running pipeline, including aliases.
    retrieval = pipeline.retrieve_context.__globals__
    index = tmp_path / "index"
    monkeypatch.setitem(retrieval, "_resolve_db_dir", lambda strategy: str(index))
    monkeypatch.setitem(retrieval, "_get_embeddings", lambda: NvidiaEmbeddings("synthetic-model"))
    monkeypatch.setitem(retrieval, "EMBEDDING_PROVIDER", "nvidia")
    store = retrieval["load_vectorstores"]()
    store.add_texts(["Đái tháo đường týp 2: 70 mg/dL; synthetic-document@example.invalid"], metadatas=[{"source_id": "synthetic-guideline", "page_numbers": "1"}])
    assert len(retrieval["cached_documents"]()) == 1
    monkeypatch.setattr(long_term, "EMBEDDING_PROVIDER", "nvidia")
    monkeypatch.setattr(long_term, "NVIDIA_EMBEDDING_MODEL", "synthetic-model")
    monkeypatch.setattr(pipeline, "get_long_term_memory", lambda owner: long_term.LongTermMemory(user_id=owner, memory_db_dir=str(tmp_path / "memory")))
    # Reranking is local and optional; no model download during the capture run.
    monkeypatch.setattr(pipeline, "rerank_contexts", lambda question, contexts, top_n: contexts[:top_n])
    monkeypatch.setattr(pipeline, "validate_context_provenance", lambda contexts: None)
    # A fresh real client avoids any earlier test's mocked generator client.
    generation = pipeline.generate_answer.__globals__
    monkeypatch.setitem(generation, "client", nvidia.RotatingNvidiaClient())
    pipeline_errors = []
    original_rag_chat = pipeline.rag_chat
    def capture_rag_error(*args, **kwargs):
        try:
            return original_rag_chat(*args, **kwargs)
        except Exception as exc:
            import traceback
            pipeline_errors.append(traceback.format_exc())
            raise
    monkeypatch.setattr(pipeline, "rag_chat", capture_rag_error)
    a, ta = make_user(username="synthetic-owner-a")
    b, tb = make_user(username="synthetic-owner-b")
    calls.clear()
    for user, token, marker in [(a, ta, "A_PRIVATE_HISTORY"), (b, tb, "B_PRIVATE_HISTORY"), (a, ta, "A_SECOND"), (b, tb, "B_SECOND")]:
        before = len(calls)
        response = client.post("/v1/query", headers={"Authorization": f"Bearer {token}"}, json={"query": f"Đái tháo đường týp 2; {marker}; synthetic-query@example.invalid; 70 mg/dL"})
        assert response.status_code == 200, f"synthetic API flow failed: {response.text}; {pipeline_errors}"
        body = response.json()
        assert body.get("cache_hit") is False
        assert body.get("effective_user_id") == user["id"]
        encoded = json.dumps(calls[before:], ensure_ascii=False)
        assert "example.invalid" not in encoded, "synthetic identifier crossed boundary"
        other = "A_PRIVATE_HISTORY" if user["id"] == b["id"] else "B_PRIVATE_HISTORY"
        assert other not in encoded and other not in json.dumps(body), "cross-owner disclosure"
    # Exercise summary/export, then simultaneous requests and the real SSE route.
    assert "A_PRIVATE_HISTORY" not in json.dumps(pipeline.get_long_term_memory(b["id"]).get_user_profile(), ensure_ascii=False)
    assert "B_PRIVATE_HISTORY" not in json.dumps(pipeline.get_long_term_memory(a["id"]).get_user_profile(), ensure_ascii=False)
    own_episodic = pipeline.get_episodic_memory(a["id"])
    own_episodic._create_summary()
    assert "B_PRIVATE_HISTORY" not in json.dumps(own_episodic.to_dict(), ensure_ascii=False)
    assert "A_PRIVATE_HISTORY" not in json.dumps(pipeline.get_episodic_memory(b["id"]).to_dict(), ensure_ascii=False)
    from concurrent.futures import ThreadPoolExecutor
    def ask(pair):
        user, token, marker, other = pair
        result = client.post("/v1/query", headers={"Authorization": f"Bearer {token}"}, json={"query": f"Đái tháo đường týp 2; {marker}; 70 mg/dL"})
        assert result.status_code == 200
        assert other not in json.dumps(result.json())
    with ThreadPoolExecutor() as pool:
        list(pool.map(ask, [(a, ta, "A_PRIVATE_HISTORY", "B_PRIVATE_HISTORY"), (b, tb, "B_PRIVATE_HISTORY", "A_PRIVATE_HISTORY")]))
    streamed = client.post("/v1/query/stream", headers={"Authorization": f"Bearer {tb}"}, json={"query": "Đái tháo đường týp 2; B_PRIVATE_HISTORY; synthetic-stream@example.invalid"})
    assert streamed.status_code == 200 and "event: done" in streamed.text
    assert "A_PRIVATE_HISTORY" not in streamed.text
    for call in calls:
        encoded = json.dumps(call, ensure_ascii=False)
        assert not ("A_PRIVATE_HISTORY" in encoded and "B_PRIVATE_HISTORY" in encoded)
        assert "example.invalid" not in encoded
    before = len(calls)
    blocked = client.post("/v1/query", headers={"Authorization": f"Bearer {tb}"}, json={"query": "Đái tháo đường týp 2; địa chỉ: số 12 phố thử"})
    assert blocked.status_code == 422
    assert len(calls) == before


def test_gold_policy_and_clinical_preservation(tmp_path):
    """Small labeled synthetic set; blocked requests count as contained, not redacted."""
    from src.shared.privacy import POLICY_VERSION, identity_scope
    positives = [
        ("phone", "Gọi +84 912 345 678", "+84 912 345 678"),
        ("email", "Liên hệ synthetic@example.invalid", "synthetic@example.invalid"),
        ("id", "CCCD: 001 234 567 890", "001 234 567 890"),
        ("name", "Tôi tên Nguyễn Văn An; không khó thở", "Nguyễn Văn An"),
        ("name", "toi ten nguyen van an; khong kho tho", "nguyen van an"),
        ("name", "Nguyễn Văn An có glucose 70 mg/dL", "Nguyễn Văn An"),
        ("address", "địa chỉ: 12 đường thử", "12 đường thử"),
        ("address", "dia chi: so 12 duong thu", "so 12 duong thu"),
        ("dob", "ngày sinh: 1980-02-01", "1980-02-01"),
        ("dob", "01/02/1980", "01/02/1980"),
        ("record", "BHYT: DN40123456789", "DN40123456789"),
        ("username", "synthetic-owner", "synthetic-owner"),
        ("url", "https://example.invalid/patient?token=synthetic", "token=synthetic"),
        ("unicode", "Tôi tên Nguyễn Văn An", "Nguyễn Văn An"),
    ]
    negatives = [f"Glucose {v} mg/dL; không khó thở; hôm qua" for v in [69, 70, 250, 251, 299, 300]] + ["7.0 mmol/L", "ADA Standards of Care 2024", "WHO Classification of Diabetes 2019"]
    false_negative = false_positive = blocked = 0
    with identity_scope("synthetic-owner"):
        for _, text, span in positives:
            try:
                result = redact_text(text)
            except PrivacyError:
                blocked += 1
            else:
                false_negative += int(span in result)
        for text in negatives:
            try:
                false_positive += int(redact_text(text) != text)
            except PrivacyError:
                false_positive += 1
    report = {"policy": POLICY_VERSION, "synthetic_only": True, "positive_cases": len(positives), "negative_cases": len(negatives), "blocked": blocked, "false_negative": false_negative, "false_positive": false_positive, "limits": ["small synthetic gold set", "unmarked names/addresses outside rules are not covered", "public author names may require local review"]}
    # Fixed report contains only metrics/policy/limitations, never source text.
    from pathlib import Path
    target = Path("test-results/privacy-gold-metrics.json")
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    assert false_negative == 0
    assert false_positive == 0


def test_failure_messages_never_echo_provider_body(capture):
    calls, statuses = capture
    statuses.append(400)
    with pytest.raises(RuntimeError, match="NVIDIA chat request failed") as err:
        nvidia.RotatingNvidiaClient().chat.completions.create(model="test", messages=[{"role": "user", "content": "synthetic@example.invalid"}])
    assert "example.invalid" not in str(err.value)


def test_judge_policy_error_does_not_fallback(capture):
    from src.reviews.evaluator import evaluate_rag
    calls, _ = capture
    with pytest.raises(PrivacyError):
        evaluate_rag("Đái tháo đường; địa chỉ: số 12 phố thử", "answer", [])
    assert not calls


def test_glucose_sequence_is_not_a_national_id():
    text = "69 70 250 251 299 300 mg/dL; không khó thở"
    assert redact_text(text) == text


@pytest.mark.parametrize("text", [
    "Mẹ tôi là Lê Thị Bích, glucose 120 mg/dL",
    "benh nhan Nguyen Van An dang theo doi duong huyet",
    "vợ tôi tên Trần Ngọc Mai",
    "Tôi ở số 12 đường Nguyễn Trãi",
    "song tai 27 pho Hue",
    "thường trú: 18A/2 hẻm 4",
    "patient John Michael Smith has diabetes",
    "Họ tên: N.V.A.",
    "ho ten: T T H",
    "Bố tôi là Phạm Minh Đức",
    "me toi ten Do Thi Lan",
    "anh tôi tên Hồ Quang Huy",
    "chi toi la Ngo Mai Anh",
    "Con tôi Nguyễn Hà My đang dùng metformin",
    "Patient Maria Garcia Lopez has diabetes",
    "My name is Robert James Brown",
    "địa chỉ: 45 Nguyễn Du, Hà Nội",
    "dia chi 18 Tran Phu, Da Nang",
    "nhà ở 7B phố Huế",
    "nha o 12/4 hem 8",
    "ngụ tại 3 đường Lê Lợi",
    "ngu tai 91 duong Cach Mang Thang Tam",
    "tạm trú: 22 thôn Đông",
    "tam tru 5 ap Hoa Binh",
    "live at 221 Baker Street",
    "reside at 10 Downing Street",
])
def test_freeform_name_and_address_are_blocked(text):
    try:
        safe = redact_text(text)
    except PrivacyError as exc:
        assert "identity_requires_edit" in str(exc)
    else:
        assert "[REDACTED]" in safe


@pytest.mark.parametrize("text", [
    "Người bệnh không khó thở và glucose 120 mg/dL",
    "Đường huyết 69 70 250 251 299 300 mg/dL",
    "WHO PEN 2020 hướng dẫn chăm sóc ban đầu",
    "Ăn 1/2 bát cơm và đi bộ 30 phút",
    "Theo dõi trong 7 ngày, hôm qua không chóng mặt",
    "Bệnh nhân không có địa chỉ email trong hồ sơ này",
    "Địa chỉ IP không được dùng trong hướng dẫn này",
    "WHO Classification of Diabetes Mellitus 2019",
    "Nguyễn và cộng sự được trích trong tài liệu công khai",
    "Đi bộ tại nhà 30 phút mỗi ngày",
])
def test_freeform_detector_preserves_clinical_text(text):
    assert redact_text(text) == text


def test_verified_public_scope_allows_only_exact_chunk():
    public = "Author Nguyễn Văn A. WHO public guideline."
    with verified_public_scope([public]):
        assert redact_text(public) == public
        with pytest.raises(PrivacyError):
            redact_text("Patient John Michael Smith private addition")


def test_retriever_public_bypass_requires_verified_flag():
    from src.chat.retriever import trim_text
    public = "WHO public\u200b guideline"
    assert trim_text(public, verified_public=True) == public
    with pytest.raises(PrivacyError):
        trim_text(public)


def test_provenance_allows_only_verified_scope_sources():
    from src.shared.models.llm_io import ContextItem
    import chromadb
    root = Path(__file__).resolve().parents[1]
    collection = chromadb.PersistentClient(path=str(root / "embeddings" / "pdf_db_nvidia_verified_20261102" / "hybrid_section_semantic")).get_collection("langchain")
    row = collection.get(limit=1, include=["documents", "metadatas"])
    validate_context_provenance([
        ContextItem(source_id=row["metadatas"][0]["source_id"], content=row["documents"][0],
                    chunk_hash=row["metadatas"][0]["chunk_hash"]),
        ContextItem(source_id="short_term_memory", content="private but redacted later"),
        ContextItem(source_id="gho_stats", content="public aggregate"),
    ])


def test_actual_gho_injection_reaches_sanitized_transport(capture):
    from src.chat.rag_pipeline import maybe_inject_gho_stats
    calls, _ = capture
    contexts = maybe_inject_gho_stats("Tỷ lệ đái tháo đường tại Việt Nam thay đổi thế nào?", [])
    assert contexts and contexts[0].source_id == "gho_stats"
    validate_context_provenance(contexts)
    nvidia.RotatingNvidiaClient().chat.completions.create(
        model="test", messages=[{"role": "user", "content": contexts[0].content}])
    assert len(calls) == 1
    assert "Global Health Observatory" in json.dumps(calls[0], ensure_ascii=False)


@pytest.mark.parametrize("source_id", [
    "ada_standards_of_care_2024_abridged",
    "byt_qd5481_hd_chandoan_dtd_type2_2020",
    "who_mental_health_at_work_2022",
    "unknown_source",
])
def test_provenance_blocks_unverified_or_out_of_scope_sources(source_id):
    from src.shared.models.llm_io import ContextItem
    with pytest.raises(PrivacyError, match="corpus_"):
        validate_context_provenance([ContextItem(source_id=source_id, content="blocked")])
