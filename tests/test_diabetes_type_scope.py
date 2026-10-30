import sqlite3
import asyncio

from src.auth import db
from src.diabetes.scope_guard import is_type2_patient, safeguard_response
from src.chat.router import _scope_answer, rag_query, rag_query_stream
from src.chat.schemas import QueryRequest


def test_existing_auth_db_migrates_to_unknown(tmp_path, monkeypatch):
    path = tmp_path / "auth.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE, hashed_password TEXT NOT NULL, full_name TEXT, role TEXT NOT NULL, is_active INTEGER DEFAULT 1, is_verified INTEGER DEFAULT 1, created_at TEXT NOT NULL, last_login TEXT)")
        conn.execute("INSERT INTO users (id,username,hashed_password,role,created_at) VALUES ('old','old','hash','user','2026-01-01')")
    monkeypatch.setattr(db, "AUTH_DB_PATH", path)
    db.init_auth_db()
    db.init_auth_db()
    assert db.get_user_by_id("old")["diabetes_type"] == "unknown"
    new = db.create_user("new", None, "hash", None, "user", diabetes_type="type2")
    assert new["diabetes_type"] == "type2"
    assert db.update_user(new["id"], diabetes_type="type1")["diabetes_type"] == "type1"


def test_type_gate_and_emergency_priority():
    question = "Tôi muốn hỏi về đường huyết"
    for typ in ("type1", "unknown"):
        user = {"id": "u", "role": "user", "diabetes_type": typ}
        assert not is_type2_patient(user)
        assert _scope_answer(question, user) == safeguard_response(question)
        assert "115" in _scope_answer("Tôi bị méo miệng và yếu nửa người", user)
    assert _scope_answer(question, {"id": "u", "role": "user", "diabetes_type": "type2"}) is None


def test_both_chat_paths_gate_before_retrieval():
    user = {"id": "u", "role": "user", "diabetes_type": "type1"}
    req = QueryRequest(query="Đường huyết của tôi thế nào?")
    assert rag_query(req, user)["answer"] == safeguard_response(req.query)
    stream = rag_query_stream(req, user)
    async def read_stream():
        pieces = [chunk.decode() if isinstance(chunk, bytes) else chunk async for chunk in stream.body_iterator]
        return "".join(pieces)
    assert "safeguard" in asyncio.run(read_stream())
