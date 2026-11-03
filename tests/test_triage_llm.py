from types import SimpleNamespace


def test_llm_uses_json_mode_without_reasoning(monkeypatch):
    import src.shared.nvidia as nvidia
    import src.triage.triage_nlu as nlu

    calls = []
    content = (
        '{"symptoms":[{"code":"hyperglycemia","text":"khát nhiều"}],'
        '"urgency":"soon","specialty":"Endocrinology_General",'
        '"time_constraints":{"excluded_weekdays":["Wednesday"]},'
        '"requested_doctor":null,"intents":["booking","invalid"]}'
    )
    completions = SimpleNamespace(create=lambda **kwargs: calls.append(kwargs) or SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason="stop")]
    ))
    monkeypatch.setattr(nvidia, "llm_client", lambda: SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    ))

    parsed = nlu._parse_llm("khát nhiều, muốn khám trừ T4")

    assert parsed["intents"] == ["booking"]
    assert parsed["time_constraints"]["excluded_weekdays"] == ["Wednesday"]
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}


def test_llm_payload_drops_wrong_shapes():
    from src.triage.triage_nlu import _validate_llm_payload

    parsed = _validate_llm_payload({
        "symptoms": ["khát nhiều", {"code": "invented", "text": "x"}],
        "urgency": "thấp", "specialty": "Nội tổng quát",
        "time_constraints": "T4", "requested_doctor": 42,
        "intents": "khám bệnh",
    })

    assert parsed == {
        "symptoms": [], "urgency": "routine",
        "specialty": "Endocrinology_General",
        "time_constraints": {"excluded_weekdays": []},
        "requested_doctor": None, "intents": [],
    }


def test_llm_semantics_are_checked_against_text():
    from src.triage.triage_nlu import _validate_llm_payload

    parsed = _validate_llm_payload({
        "symptoms": [{"code": "neuropathy", "text": "tê rần"}],
        "urgency": "soon", "specialty": "Endocrinology_General",
        "time_constraints": {"excluded_weekdays": ["Tuesday"]},
        "requested_doctor": None, "intents": ["booking", "symptom_note"],
    }, "tê rần, muốn khám tuần sau trừ T4")

    assert parsed["specialty"] == "Endocrinology_Complication"
    assert parsed["time_constraints"]["excluded_weekdays"] == ["Wednesday"]
    assert parsed["intents"] == ["booking", "symptom_note"]


def test_llm_failure_is_logged_and_falls_back(monkeypatch, caplog):
    import src.shared.nvidia as nvidia
    import src.triage.triage_nlu as nlu

    completions = SimpleNamespace(
        create=lambda **kwargs: (_ for _ in ()).throw(TimeoutError("offline"))
    )
    monkeypatch.setattr(nvidia, "llm_client", lambda: SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    ))

    with caplog.at_level("WARNING"):
        assert nlu._parse_llm("khát nhiều") is None
    assert "reason=TimeoutError" in caplog.text
