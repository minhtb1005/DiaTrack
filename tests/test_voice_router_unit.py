"""Voice transcript contract without importing the full API/model stack."""
import asyncio
import io

from fastapi import UploadFile

from src.voice.router import transcribe_voice


def _transcribe(monkeypatch, text):
    import src.voice.providers as providers

    class STT:
        def transcribe(self, audio_bytes, content_type=""):
            return text

    monkeypatch.setattr(providers, "get_stt_provider", lambda: STT())
    upload = UploadFile(filename="voice.webm", file=io.BytesIO(b"voice"), headers={"content-type": "audio/webm"})
    return asyncio.run(transcribe_voice(upload, current_user={"id": "test"}))


def test_transcript_returns_clock_and_glucose_separately(monkeypatch):
    result = _transcribe(monkeypatch, "110 lúc đói lúc 7 giờ sáng")
    assert result["parse"]["value"] == 110
    assert result["measurement_time"] is not None
    assert result["emergency"] is False


def test_numeric_danger_warns_before_context_or_clock(monkeypatch):
    result = _transcribe(monkeypatch, "65")
    assert result["parse"]["reason"] == "no_context"
    assert result["emergency"] is True
    assert result["red_flag_type"] == "glucose_low"
