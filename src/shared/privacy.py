"""Local outbound policy. Redaction reduces exposure; it is not anonymization."""
from __future__ import annotations

import re
import json
import unicodedata
import hashlib
from collections import Counter
from contextvars import ContextVar
from contextlib import contextmanager

_known_identifiers = ContextVar("privacy_identifiers", default=())
_verified_public_hashes = ContextVar("verified_public_hashes", default=frozenset())


@contextmanager
def identity_scope(*identifiers):
    token = _known_identifiers.set(tuple(v for v in identifiers if isinstance(v, str) and v))
    try:
        yield
    finally:
        _known_identifiers.reset(token)


@contextmanager
def verified_public_scope(texts):
    """Allow only exact public chunks already derived from hash-verified files."""
    hashes = frozenset(hashlib.sha256(text.encode("utf-8")).hexdigest() for text in texts)
    token = _verified_public_hashes.set(hashes)
    try:
        yield
    finally:
        _verified_public_hashes.reset(token)

POLICY_VERSION = "2026-11-02.3"


class PrivacyError(ValueError):
    """Safe to log: never includes the rejected value."""

    def __init__(self, reason="unsupported_payload"):
        super().__init__(f"privacy:{POLICY_VERSION}:{reason}")


# Explicit identifiers only. Uncertain identity-bearing text is rejected below.
_PATTERNS = {
    "email": r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
    "url": r"(?:https?://|www\.)[^\s<>\"']+",
    "local_path": r"(?:[A-Za-z]:[\\/]|file://|/Users/|/home/)[^\s<>\"']+",
    "phone": r"(?<!\d)(?:\+84|0084|0)[ .-]{0,3}(?:\d[ .-]{0,3}){8,10}(?!\d)",
    "national_id": r"(?<![\d.])(?:\d{12}|\d{9}|\d{3}[ -]\d{3}[ -]\d{3}(?:[ -]\d{3})?)(?![ -]?\d)(?!\s*(?i:mg/dl|mmol/l))",
    "birth_date": r"(?<!\d)(?:0?[1-9]|[12]\d|3[01])[/.-](?:0?[1-9]|1[0-2])[/.-](?:19|20)\d{2}(?!\d)",
    "record_id": r"(?i)(?:CCCD|CMND|BHYT|mã bệnh án|ma benh an|medical record|patient_id|username)\s*[:=#]\s*[\w@.+/-]+",
}
_RULES = {k: re.compile(v) for k, v in _PATTERNS.items()}
_CAP = r"[A-ZÀ-ỸĐ][a-zà-ỹđ]+"
_NAME = re.compile(rf"(?i:họ tên|ho ten|tên bệnh nhân|ten benh nhan|tôi tên|toi ten|my name is|patient name|người thân|nguoi than)\s*[:=]?\s*{_CAP}(?:\s+{_CAP}){{1,5}}")
_UNCERTAIN = re.compile(r"(?i)\b(?:họ tên|ho ten|tôi tên|toi ten|tên bệnh nhân|ten benh nhan|người thân|nguoi than|my name is|patient name|địa chỉ|dia chi|address|sinh ngày|sinh ngay|ngày sinh|ngay sinh|date of birth|username)\b\s*[:=]?\s*(?!\[REDACTED\]|IP\b|email\b)\S")
_PERSON_HINT = re.compile(r"\b(?:Nguyễn|Nguyen|Trần|Tran|Lê|Le|Phạm|Pham|Hoàng|Hoang|Huỳnh|Huynh|Võ|Vo|Vũ|Vu|Đặng|Dang|Bùi|Bui|Đỗ|Do|Hồ|Ho|Ngô|Ngo|Dương|Duong)\s+[A-ZĐÀÁẢÃẠĂÂÊÔƠƯ][^\W\d_]+(?:\s+[A-ZĐÀÁẢÃẠĂÂÊÔƠƯ][^\W\d_]+)+")
_RELATION_NAME = re.compile(
    rf"(?i:\b(?:bệnh nhân|benh nhan|người bệnh|nguoi benh|mẹ tôi|me toi|bố tôi|bo toi|"
    rf"ba tôi|ba toi|vợ tôi|vo toi|chồng tôi|chong toi|con tôi|con toi|anh tôi|anh toi|"
    rf"chị tôi|chi toi|ông tôi|ong toi|bà tôi|ba toi|patient)\s*(?:tên|ten|là|la|:)?\s*"
    rf"){_CAP}(?:\s+{_CAP}){{1,5}}"
)
_ADDRESS_HINT = re.compile(
    r"\b(?:tôi ở|toi o|nhà ở|nha o|sống tại|song tai|thường trú|thuong tru|"
    r"tạm trú|tam tru|ngụ tại|ngu tai|live at|reside at)\b\s*[:=]?\s*(?!nhà\b|nha\b)\S|"
    r"\b(?:số\s+|so\s+)?\d+[A-Za-z]?(?:[/.-]\d+)?\s+(?:đường|duong|phố|pho|"
    r"ngõ|ngo|hẻm|hem|ấp|ap|thôn|thon)\b",
    re.IGNORECASE,
)
_SENSITIVE_KEYS = {"name", "user", "username", "patient_id", "user_id", "address", "full_name", "dob", "birth_date", "phone", "telephone", "email", "cccd", "cmnd", "bhyt", "họ tên", "ho ten", "tên", "địa chỉ", "dia chi", "ngày sinh", "ngay sinh", "mã bệnh án", "ma benh an"}


def redact_text(text: str, counts: Counter | None = None) -> str:
    text = unicodedata.normalize("NFC", text)
    if hashlib.sha256(text.encode("utf-8")).hexdigest() in _verified_public_hashes.get():
        return text
    if any(unicodedata.category(ch) == "Cf" for ch in text):
        raise PrivacyError("invisible_characters")
    for identifier in sorted(_known_identifiers.get(), key=len, reverse=True):
        text, n = re.subn(r"(?<!\w)" + re.escape(identifier) + r"(?!\w)", "[REDACTED]", text, flags=re.IGNORECASE)
        if counts is not None:
            counts["known_identity"] += n
    for kind, rule in [("person", _NAME), *_RULES.items()]:
        text, n = rule.subn("[REDACTED]", text)
        if counts is not None:
            counts[kind] += n
    if (_PERSON_HINT.search(text) or _RELATION_NAME.search(text)
            or _ADDRESS_HINT.search(text) or _UNCERTAIN.search(text)):
        raise PrivacyError("identity_requires_edit")
    return text


def sanitize(value, counts: Counter | None = None):
    """Copy JSON data, including keys; reject non-JSON and media payloads."""
    if isinstance(value, str):
        if value.lstrip().startswith(("{", "[")):
            try:
                parsed = json.loads(value)
            except ValueError:
                if value.lstrip().startswith(("{", '["', "[{")):
                    raise PrivacyError("invalid_json_text") from None
            else:
                return json.dumps(sanitize(parsed, counts), ensure_ascii=False)
        return redact_text(value, counts)
    if value is None or type(value) in (bool, int, float):
        return value
    if isinstance(value, list):
        return [sanitize(v, counts) for v in value]
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise PrivacyError()
            if key in {"image_url", "input_audio", "file", "audio", "video_url"}:
                raise PrivacyError("unsupported_media")
            safe_key = redact_text(key, counts)
            if safe_key in out:
                raise PrivacyError("key_collision")
            if key.lower() in _SENSITIVE_KEYS:
                out[safe_key] = "[REDACTED]"
                if counts is not None:
                    counts["identity_field"] += 1
            else:
                out[safe_key] = sanitize(item, counts)
        return out
    raise PrivacyError()


# Only these SDK controls bypass data redaction. Unknown kwargs fail closed.
_CONTROLS = {"model", "temperature", "top_p", "max_tokens", "max_completion_tokens", "stream", "stream_options", "n", "seed", "presence_penalty", "frequency_penalty", "logprobs", "top_logprobs", "parallel_tool_calls", "timeout"}
_DATA = {"messages", "tools", "tool_choice", "response_format", "metadata", "user", "extra_body", "stop", "functions", "function_call", "prediction"}


def sanitize_chat(kwargs: dict) -> dict:
    if set(kwargs) - _CONTROLS - _DATA:
        raise PrivacyError("unsupported_chat_field")
    result = {}
    for key, value in kwargs.items():
        if key in _CONTROLS:
            if key == "model":
                if not isinstance(value, str) or not re.fullmatch(r"[\w./:-]+", value):
                    raise PrivacyError("invalid_model")
            elif key != "timeout":
                # Controls must not become an alternate text channel.
                if isinstance(value, str):
                    raise PrivacyError("invalid_control")
                def control(v):
                    if v is None or type(v) in (bool, int, float):
                        return
                    if isinstance(v, dict) and all(isinstance(k, str) and k in {"include_usage", "include_obfuscation"} for k in v):
                        for item in v.values():
                            control(item)
                        return
                    raise PrivacyError("invalid_control")
                control(value)
            elif type(value) not in (int, float):
                raise PrivacyError("invalid_timeout")
            result[key] = value
        else:
            result[key] = "[REDACTED]" if key == "user" else sanitize(value)
    if not isinstance(result.get("messages"), list):
        raise PrivacyError("invalid_messages")
    return result
