"""vn_parse gold — Vietnamese spoken numbers, ±dau, zero-error policy.

Any gold fail = fix parser, never lower the bar. Ambiguous cases must
return need-re-speak (ambiguous=True), never a guess.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timedelta, timezone

from src.voice.vn_parse import parse_vi, parse_measurement_time
from tests._helpers import assert_parse_ambiguous, assert_parse_ok


def _ok(text, value, context):
    assert_parse_ok(parse_vi, text, value, context)


def _amb(text):
    assert_parse_ambiguous(parse_vi, text)


def test_digits_passthrough_accented():
    _ok("126 lúc đói", 126, "fasting")
    _ok("280 lúc đói", 280, "fasting")


def test_digits_passthrough_unaccented():
    _ok("126 luc doi", 126, "fasting")
    _ok("140 sau an", 140, "post_meal_2h")


def test_words_compound():
    _ok("một trăm hai mươi sáu lúc đói", 126, "fasting")
    _ok("mot tram hai muoi sau luc doi", 126, "fasting")


def test_words_tam_ba():
    _ok("một trăm tám lúc đói", 108, "fasting")
    _ok("một trăm ba lúc đói", 103, "fasting")


def test_ruoi_le():
    _ok("một trăm rưỡi lúc đói", 150, "fasting")
    _ok("mot tram le sau luc doi", 106, "fasting")


def test_nghin_out_of_range_ambiguous():
    _amb("một nghìn lúc đói")


def test_decimal_ambiguous():
    _amb("một trăm phẩy năm lúc đói")
    _amb("126 chấm 5 lúc đói")


def test_range_ambiguous():
    _amb("từ 100 đến 120 lúc đói")
    _amb("100-120 lúc đói")


def test_mixed_digit_words_ambiguous():
    _amb("1 trăm lúc đói")


def test_no_context_ambiguous():
    _amb("một trăm hai mươi sáu")
    _amb("126")


def test_no_number_ambiguous():
    _amb("lúc đói")
    _amb("xin chào")


def test_out_of_range_ambiguous():
    _amb("10 lúc đói")
    _amb("700 lúc đói")


def test_context_variants():
    _ok("140 sau ăn", 140, "post_meal_2h")
    _ok("110 trước ngủ", 110, "bedtime")
    _ok("95 trước ăn", 95, "pre_meal")


def test_multi_number_ambiguous():
    _amb("126 và 140 lúc đói")


def test_explicit_clock_is_separate_from_glucose_value():
    _ok("110 lúc đói lúc 7 giờ sáng", 110, "fasting")
    now = datetime(2026, 10, 30, 9, 0, tzinfo=timezone(timedelta(hours=7)))
    assert parse_measurement_time("lúc 7 giờ sáng", now) == "2026-10-30T07:00:00+07:00"
    assert parse_measurement_time("hôm qua lúc 8 giờ tối", now) == "2026-10-29T20:00:00+07:00"


def test_clock_never_guesses_missing_daypart_or_future_time():
    now = datetime(2026, 10, 30, 9, 0, tzinfo=timezone(timedelta(hours=7)))
    assert parse_measurement_time("lúc 7 giờ", now) is None
    assert parse_measurement_time("lúc 10 giờ sáng", now) is None
    assert parse_measurement_time("sau ăn 2 giờ", now) is None
    assert parse_measurement_time("7 giờ sáng hôm qua", now) is None
    assert parse_measurement_time("12 giờ tối", now) is None
    assert parse_vi("110 lúc 8 giờ tối")["reason"] == "no_context"
