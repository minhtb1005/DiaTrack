"""Parse spoken Vietnamese glucose numbers — pure, no-guess, zero-error policy.

parse_vi(text) -> {value, context, ambiguous, reason, confirm_text}

AMBIGUOUS (= must re-speak, never guess) when: missing context, value
outside 20-600, decimals (phay/cham), ranges (tu X den Y / X-Y), mixed
digits+words, or no number at all. "ruoi/linh/nghin" parse exactly when
clear (tram ruoi=150, tram le sau=106, nghin->out-of-range->ambiguous).
Digits passthrough ("126 luc doi" -> 126, no re-parse).
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional


try:
    from src.shared.text import unaccent as _unaccent
except ImportError:  # pragma: no cover
    try:
        from shared.text import unaccent as _unaccent  # type: ignore
    except ImportError:
        def _unaccent(s: str) -> str:  # fallback NFD-strip
            out = "".join(
                c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn"
            )
            return out.replace("đ", "d").replace("Đ", "D").lower()


_UNITS = {
    "khong": 0, "mot": 1, "hai": 2, "ba": 3, "bon": 4, "tu": 4,
    "nam": 5, "lam": 5, "sau": 6, "bay": 7, "tam": 8, "chin": 9,
}

_CONTEXTS = (
    ("fasting", ("doi", "luc doi", "sang som", "fasting", "bung doi")),
    ("post_meal_2h", ("sau an", "no", "after", "2h", "hai gio")),
    ("bedtime", ("truoc ngu", "toi", "dem", "bedtime", "di ngu")),
    ("pre_meal", ("truoc an", "pre",)),
)

VN_TZ = timezone(timedelta(hours=7))
_TIME_RE = re.compile(
    r"\b(?:(?P<day>hom qua|hom nay|sang nay|chieu nay|toi nay)\s+)?"
    r"(?:(?:luc|vao)\s+)?(?P<hour>\d{1,2})\s*(?:gio|h)"
    r"(?:\s*(?P<minute>\d{1,2})\s*(?:phut)?)?\s*"
    r"(?P<period>sang|trua|chieu|toi|dem)?\b"
)


def parse_measurement_time(text: str, now: Optional[datetime] = None) -> Optional[str]:
    """Return an explicit, non-future Vietnam measurement time; never guess AM/PM."""
    t = _unaccent(text or "")
    matches = list(_TIME_RE.finditer(t))
    if len(matches) != 1:
        return None
    m = matches[0]
    # "sau an 2 gio" is a context, not a clock reading.
    if t[max(0, m.start() - 7):m.start()].strip().endswith("sau an"):
        return None
    day, period = m.group("day"), m.group("period")
    if "hom qua" in t and day != "hom qua":
        return None  # date after the clock is unsupported; do not store today
    period = period or {"sang nay": "sang", "chieu nay": "chieu", "toi nay": "toi"}.get(day or "")
    if not period:
        return None
    hour, minute = int(m.group("hour")), int(m.group("minute") or 0)
    if minute > 59 or hour > 23:
        return None
    if hour == 12 and period in ("toi", "dem"):
        return None  # midnight/noon wording needs clarification
    if period in ("chieu", "toi", "dem") and hour <= 12:
        hour = hour % 12 + 12
    elif period in ("sang", "trua") and hour > 12:
        return None
    current = (now or datetime.now(VN_TZ)).astimezone(VN_TZ)
    date = current.date() - timedelta(days=1 if day == "hom qua" else 0)
    measured = datetime.combine(date, datetime.min.time(), VN_TZ).replace(hour=hour, minute=minute)
    return measured.isoformat() if measured <= current else None


def _without_clock(text: str) -> str:
    """Remove only clock phrases with an explicit daypart, preserving 'sau an 2 gio'."""
    return _TIME_RE.sub(lambda m: " " if m.group("period") or m.group("day") else m.group(0), text)


def _words_to_number(words: list) -> Optional[float]:
    """Vietnamese number words -> float. Returns None if no number found."""
    total = 0.0
    cur = 0.0
    seen = False
    i = 0
    n = len(words)
    while i < n:
        w = words[i]
        if w in ("le", "linh"):
            # "mot tram le sau" = 100 + 0 + 6 ; next unit adds directly
            i += 1
            if i < n and words[i] in _UNITS:
                cur += _UNITS[words[i]]
                seen = True
                i += 1
            continue
        if w == "ruoi":
            # "tram ruoi" = +50 (150); "120 ruoi" = +0.5
            cur += 50 if (cur == 0 and total > 0) else 0.5
            seen = True
            i += 1
            continue
        if w in _UNITS:
            cur += _UNITS[w]
            seen = True
            i += 1
            continue
        if w in ("muoi", "chuc"):
            cur = (cur if cur else 1) * 10
            seen = True
            i += 1
            continue
        if w == "tram":
            total += (cur if cur else 1) * 100
            cur = 0.0
            seen = True
            i += 1
            continue
        if w == "nghin":
            total += (cur if cur else 1) * 1000
            cur = 0.0
            seen = True
            i += 1
            continue
        i += 1
    if not seen:
        return None
    return total + cur


def _extract_context(t: str) -> tuple:
    for ctx, keys in _CONTEXTS:
        for k in keys:
            if k in t:
                return ctx, k
    return None, ""


def parse_vi(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    t = _unaccent(raw)
    if not t:
        return {"value": None, "context": None, "ambiguous": True,
                "reason": "empty", "confirm_text": ""}

    context, ctx_key = _extract_context(_without_clock(t))
    # Mask the matched context phrase before number parse ("sau an" would
    # otherwise read "sau" as 6).
    num_t = _without_clock(t)
    num_t = num_t.replace(ctx_key, " ", 1) if ctx_key else num_t

    # Ranges -> ambiguous (never average)
    if re.search(r"\btu\b.*\bden\b|\btoi\b.*\b\d|-|–|~|khoang", t):
        digits = re.findall(r"\d+(?:[.,]\d+)?", t)
        if len(digits) >= 2 or "den" in t or "khoang" in t:
            return {"value": None, "context": context, "ambiguous": True,
                    "reason": "range", "confirm_text": ""}
    # Decimals -> ambiguous
    if "phay" in num_t or re.search(r"\bcham\b", num_t):
        return {"value": None, "context": context, "ambiguous": True,
                "reason": "decimal", "confirm_text": ""}

    digit_vals = [float(d.replace(",", ".")) for d in re.findall(r"\d+(?:[.,]\d+)?", num_t)]
    has_digit = len(digit_vals) > 0
    words = re.findall(r"[a-z]+", num_t)
    word_val = _words_to_number(words)

    # Mixed digits + words -> ambiguous
    if has_digit and word_val is not None:
        return {"value": None, "context": context, "ambiguous": True,
                "reason": "mixed", "confirm_text": ""}

    value: Optional[float] = None
    if has_digit:
        if len(digit_vals) > 1:
            return {"value": None, "context": context, "ambiguous": True,
                    "reason": "multi_number", "confirm_text": ""}
        value = digit_vals[0]
    elif word_val is not None:
        value = word_val
    else:
        return {"value": None, "context": None, "ambiguous": True,
                "reason": "no_number", "confirm_text": ""}

    if context is None:
        return {"value": int(round(value)), "context": None, "ambiguous": True,
                "reason": "no_context", "confirm_text": ""}
    if not (20 <= value <= 600):
        return {"value": int(round(value)), "context": context, "ambiguous": True,
                "reason": "out_of_range", "confirm_text": ""}

    ivalue = int(round(value))
    label = {"fasting": "luc doi", "post_meal_2h": "sau an",
             "bedtime": "truoc ngu", "pre_meal": "truoc an"}.get(context, context)
    return {"value": ivalue, "context": context, "ambiguous": False, "reason": "",
            "confirm_text": f"Bac vua noi {ivalue} {label}, dung khong?"}
