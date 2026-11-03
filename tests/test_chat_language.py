"""M1: Vietnamese instruction wiring (not compliance) — mock LLM boundary, no key needed."""
import sys

import pytest

sys.path.insert(0, ".")

from src.chat import generator as gen

LLMInput = gen.LLMInput
ContextItem = gen.ContextItem


class _FakeMsg:
    content = "Trả lời mẫu"


class _FakeChoice:
    message = _FakeMsg()


class _FakeResp:
    choices = [_FakeChoice()]
    usage = None


class _FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kw):
        self.calls.append(kw)
        return _FakeResp()


class _FakeChat:
    def __init__(self):
        self.completions = _FakeCompletions()


class _FakeClient:
    def __init__(self):
        self.chat = _FakeChat()


def _inp(lang="vi"):
    return LLMInput(query="dấu hiệu tiểu đường là gì?",
                    contexts=[ContextItem(source_id="0", content="ctx")],
                    language=lang)


def test_vi_instruction_in_system_and_user_prompt(monkeypatch):
    for _k in (
        "NVDIA_API_KEY", "NVDIA_API_KEY2", "NVDIA_API_KEY3",
        "NVIDIA_API_KEY", "NVIDIA_API_KEY2", "NVIDIA_API_KEY3",
    ):
        monkeypatch.delenv(_k, raising=False)
    fake = _FakeClient()
    monkeypatch.setattr(gen, "client", fake)
    gen.generate_answer(_inp("vi"))
    msgs = fake.chat.completions.calls[0]["messages"]
    system = next(m["content"] for m in msgs if m["role"] == "system")
    user = next(m["content"] for m in msgs if m["role"] == "user")
    assert "tiếng Việt" in system
    assert user.rstrip().endswith("Trả lời HOÀN TOÀN bằng tiếng Việt.")


def test_en_skips_vi_instruction(monkeypatch):
    for _k in (
        "NVDIA_API_KEY", "NVDIA_API_KEY2", "NVDIA_API_KEY3",
        "NVIDIA_API_KEY", "NVIDIA_API_KEY2", "NVIDIA_API_KEY3",
    ):
        monkeypatch.delenv(_k, raising=False)
    fake = _FakeClient()
    monkeypatch.setattr(gen, "client", fake)
    gen.generate_answer(_inp("en"))
    msgs = fake.chat.completions.calls[0]["messages"]
    system = next(m["content"] for m in msgs if m["role"] == "system")
    user = next(m["content"] for m in msgs if m["role"] == "user")
    assert "QUAN TRỌNG" not in system
    assert "HOÀN TOÀN" not in user


def test_query_request_defaults_language_vi():
    from src.chat.schemas import QueryRequest
    assert QueryRequest(query="x").language == "vi"


@pytest.mark.parametrize("retry_content", ["Nội dung sau retry", None])
def test_empty_hard_model_retries_once_with_more_tokens(monkeypatch, retry_content):
    from types import SimpleNamespace
    from src.shared import nvidia

    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        content = None if len(calls) == 1 else retry_content
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))], usage=None)
    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(gen, "client", fake)
    model = nvidia.hard_model()
    if retry_content:
        assert gen.generate_answer(_inp(), model=model).answer == retry_content
    else:
        with pytest.raises(RuntimeError, match="nội dung rỗng"):
            gen.generate_answer(_inp(), model=model)
    assert len(calls) == 2
    assert calls[0]["model"] == calls[1]["model"]
    assert calls[1]["max_tokens"] >= 2048
