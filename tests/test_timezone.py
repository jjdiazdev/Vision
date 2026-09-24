"""Tests for dashboard_app/app/utils/timezone_utils.py.

Deliberately DB-free and create_app-free: docs/domains/test_coverage.md records that two test
files each standing up the global Flask-SQLAlchemy `db` against different temp DBs produce
`sqlite3.OperationalError: disk I/O error` in one process. A pure-helper file sidesteps that
entirely and can run alongside anything.
"""
import os
import sys
import unittest
from datetime import date, datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from dashboard_app.app.utils.timezone_utils import (
    convert, display_now, format_display, is_valid_timezone, resolve_timezone, to_display_tz)

CARACAS = "America/Caracas"   # UTC-4, no DST -- stable for assertions


class TestResolveTimezone(unittest.TestCase):
    def test_none_empty_and_utc_shortcircuit_to_stdlib_utc(self):
        # Must NOT go through ZoneInfo: ZoneInfo("UTC") also raises when tzdata is absent,
        # so this is what makes the default configuration immune to a missing tz database.
        for value in (None, "", "UTC", "utc", "  Utc  "):
            self.assertIs(resolve_timezone(value), timezone.utc, f"for {value!r}")

    def test_real_zone_resolves(self):
        self.assertEqual(
            datetime(2026, 9, 9, 19, 12, tzinfo=timezone.utc)
            .astimezone(resolve_timezone(CARACAS)).utcoffset(),
            timedelta(hours=-4))

    def test_unknown_zone_falls_back_to_utc_without_raising(self):
        self.assertIs(resolve_timezone("Mars/Olympus"), timezone.utc)

    def test_garbage_input_does_not_raise(self):
        self.assertIs(resolve_timezone("../../etc/passwd"), timezone.utc)


class TestIsValidTimezone(unittest.TestCase):
    def test_valid(self):
        for value in (None, "", "UTC", CARACAS, "Europe/Madrid"):
            self.assertTrue(is_valid_timezone(value), f"for {value!r}")

    def test_invalid(self):
        for value in ("Mars/Olympus", "-04:00", "EST5EDT-nonsense"):
            self.assertFalse(is_valid_timezone(value), f"for {value!r}")


class TestConvert(unittest.TestCase):
    def test_naive_is_treated_as_utc(self):
        got = convert(datetime(2026, 9, 9, 19, 12), resolve_timezone(CARACAS))
        self.assertEqual((got.hour, got.minute), (15, 12))

    def test_aware_input_is_idempotent(self):
        aware = datetime(2026, 9, 9, 19, 12, tzinfo=timezone.utc)
        once = convert(aware, resolve_timezone(CARACAS))
        twice = convert(once, resolve_timezone(CARACAS))
        self.assertEqual(once, twice)

    def test_none_and_non_datetime(self):
        tz = resolve_timezone(CARACAS)
        self.assertIsNone(convert(None, tz))
        self.assertIsNone(convert(date(2026, 9, 9), tz))   # a bare date has no .astimezone
        self.assertIsNone(convert("2026-09-09", tz))


class TestFormatDisplay(unittest.TestCase):
    def test_the_reported_bug(self):
        # The exact case measured against the live DB: a notification stored 19:12 UTC was
        # rendered as 19:12 while the operator's wall clock read 15:12.
        self.assertEqual(
            format_display(datetime(2026, 9, 9, 19, 12), "%Y-%m-%d %H:%M", CARACAS),
            "2026-09-09 15:12")

    def test_utc_is_identity(self):
        self.assertEqual(
            format_display(datetime(2026, 9, 9, 19, 12), "%Y-%m-%d %H:%M", "UTC"),
            "2026-09-09 19:12")

    def test_date_only_format_can_shift_a_calendar_day(self):
        # 02:00Z is the previous day in Caracas -- this is why the "Joined At" column can
        # visibly move back one day, and why repetition boundaries needed fixing too.
        self.assertEqual(
            format_display(datetime(2026, 9, 9, 2, 0), "%Y-%m-%d", CARACAS), "2026-09-08")

    def test_none_renders_empty_never_the_string_none(self):
        self.assertEqual(format_display(None, "%Y-%m-%d", CARACAS), "")

    def test_non_datetime_renders_empty(self):
        self.assertEqual(format_display(date(2026, 9, 9), "%Y-%m-%d", CARACAS), "")

    def test_unknown_zone_degrades_to_utc_without_raising(self):
        self.assertEqual(
            format_display(datetime(2026, 9, 9, 19, 12), "%Y-%m-%d %H:%M", "Mars/Olympus"),
            "2026-09-09 19:12")

    def test_default_format(self):
        self.assertEqual(format_display(datetime(2026, 9, 9, 19, 12), tz_name=CARACAS),
                         "2026-09-09 15:12")


class TestHelpers(unittest.TestCase):
    def test_to_display_tz(self):
        self.assertEqual(to_display_tz(datetime(2026, 9, 9, 19, 12), CARACAS).hour, 15)

    def test_display_now_is_aware_and_offset_matches(self):
        self.assertEqual(display_now(CARACAS).utcoffset(), timedelta(hours=-4))
        self.assertEqual(display_now("UTC").utcoffset(), timedelta(0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
