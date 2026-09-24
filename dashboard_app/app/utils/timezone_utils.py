"""Display-timezone conversion for stored timestamps.

Convention this module exists to enforce (see docs/adr/0002-store-utc-display-local.md):
**every datetime in the database is naive UTC** (`TimestampMixin` uses `datetime.utcnow`),
and the configured timezone is applied *only* when a value is rendered or when a local
calendar day matters. Never convert before storing.

🔴 Carve-out that must not be "helpfully" unified: `execution/github_sync.py` writes its
`last_polled` cursor as a UTC ISO-8601 string and compares it lexicographically against
GitHub's own UTC `updatedAt`. That is a wire-protocol value, not a display value. Making it
local-tz would still compare "successfully" and silently return the wrong polling window --
no exception, no log, just missed or duplicated issues. Leave it alone.

Deliberately Flask-free (stdlib + dashboard_app.config only) so execution/ scripts can
import it without needing an app context.
"""
import logging
from datetime import datetime, timezone, tzinfo
from functools import lru_cache
from zoneinfo import ZoneInfo

from dashboard_app.config import Config

logger = logging.getLogger(__name__)

DEFAULT_TIMEZONE = "UTC"
DEFAULT_FORMAT = "%Y-%m-%d %H:%M"


def get_display_timezone_name():
    """The configured IANA zone name.

    Reads `Config` rather than `os.environ` on purpose: dashboard_app/config.py is the only
    place that calls load_dotenv() for both dashboard_app/.env and the repo-root .env. A bare
    os.environ lookup happens to work today only because importing dashboard_app.app.models
    executes dashboard_app/app/__init__.py, which imports Config as a side effect -- relying
    on that is fragile. This works identically in all three execution modes: gunicorn, the
    `flask process-repetitions` CLI, and a standalone `python -m execution.*` run.
    """
    return getattr(Config, "DISPLAY_TIMEZONE", None) or DEFAULT_TIMEZONE


@lru_cache(maxsize=8)
def resolve_timezone(tz_name):
    """IANA name -> tzinfo, never raising.

    The UTC path short-circuits to stdlib `datetime.timezone.utc` and never touches
    `zoneinfo`, because ZoneInfo("UTC") *also* raises when the tz database is absent. That
    makes the default configuration structurally immune to a missing tzdata.

    Cached: the notifications panel renders up to 200 rows per refresh (routes.py's
    `.limit(200)`), and this resolves once per process instead of per row. gunicorn runs
    --workers 1 --worker-class gevent, and greenlets don't preempt mid-bytecode, so the
    cache needs no lock.
    """
    if not tz_name or str(tz_name).strip().upper() == "UTC":
        return timezone.utc
    try:
        return ZoneInfo(str(tz_name).strip())
    except Exception:
        # ZoneInfoNotFoundError (a KeyError subclass) for a typo or absent tzdata, ValueError
        # for a path-like key. An lru_cache miss is the natural once-only hook, so a bad
        # value logs exactly once per process rather than on every render.
        logger.error(
            "DISPLAY_TIMEZONE=%r is not a resolvable IANA zone (typo, or tz database "
            "missing); falling back to UTC", tz_name)
        return timezone.utc


def is_valid_timezone(tz_name):
    """Whether `tz_name` resolves, for startup validation. Never raises.

    Uses a ZoneInfo() attempt rather than `name in available_timezones()`, which is a
    filesystem scan of the whole tz database.
    """
    if not tz_name or str(tz_name).strip().upper() == "UTC":
        return True
    try:
        ZoneInfo(str(tz_name).strip())
        return True
    except Exception:
        return False


def convert(dt, tz):
    """Naive-UTC (or aware) datetime -> `tz`. Pure; takes an already-resolved tzinfo so a
    caller in a loop resolves once. Idempotent for already-aware input."""
    if dt is None or not isinstance(dt, datetime) or not isinstance(tz, tzinfo):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)   # stored naive == UTC, by convention
    return dt.astimezone(tz)


def to_display_tz(dt, tz_name=None):
    """Convenience wrapper resolving the zone by name."""
    return convert(dt, resolve_timezone(tz_name if tz_name is not None
                                        else get_display_timezone_name()))


def display_now(tz_name=None):
    """`now` as an aware datetime in the configured zone. For local calendar-day logic."""
    return datetime.now(timezone.utc).astimezone(
        resolve_timezone(tz_name if tz_name is not None else get_display_timezone_name()))


def format_display(dt, fmt=DEFAULT_FORMAT, tz_name=None):
    """Render a stored datetime in the configured zone. Never raises, never returns "None".

    Returns '' for None or for a non-datetime (a bare `date` has no .astimezone() and would
    otherwise AttributeError mid-template). On any unforeseen failure it falls back to the
    raw strftime -- i.e. today's UTC behavior. Worst case is the old bug, never a 500.
    """
    if dt is None or not isinstance(dt, datetime):
        return ""
    try:
        return convert(dt, resolve_timezone(
            tz_name if tz_name is not None else get_display_timezone_name())).strftime(fmt)
    except Exception:
        logger.warning("format_display failed for %r; rendering raw UTC", dt, exc_info=True)
        try:
            return dt.strftime(fmt)
        except Exception:
            return ""
