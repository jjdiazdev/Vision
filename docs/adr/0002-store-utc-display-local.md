# ADR 0002: Store timestamps in UTC, convert only for display

## Status

Accepted

## Date

2026-09-09

## Context

Every datetime in the database is naive UTC: `TimestampMixin`
(`dashboard_app/app/models.py`) defaults `created_at`/`updated_at` to `datetime.utcnow`, and
every migration declares `sa.DateTime()` with no `timezone=True`. The containers run with no
`TZ` set, so their clock is UTC.

Nothing wrote this convention down anywhere in `docs/`, and two defects grew out of that
silence:

1. **Notification History showed the wrong time.** The panel rendered the stored value raw.
   Measured on 2026-09-09: a notification stored `21:43` displayed as `21:43` while the
   operator's wall clock read `17:43` — four hours out, the host being `America/Caracas`
   (UTC-04). The Employees table's "Joined At" column had the same defect.
2. **Repeat_\* Tasks reset at the wrong moment.** `execution/repetition_processor.py` compared
   `updated_at.date() < today.date()` with both sides in UTC, so a "daily" Task rolled over at
   20:00 the operator's time. Nobody noticed, because there was no stated convention to check
   the code against.

Alternatives seriously considered:

- **Store local time instead.** Rejected: it corrupts the meaning of a decade of existing rows
  with no marker to distinguish them, and it would break `execution/github_sync.py`'s polling
  cursor (below).
- **Set the `TZ` environment variable.** Rejected, and this is the most tempting wrong answer.
  `TZ` is read by glibc, so it silently changes `datetime.now()`, `time.localtime()`, gunicorn
  access-log timestamps, `date` in the container and SQLite's `localtime` modifier —
  process-wide, for every service. The specific hazard: any future `datetime.now()` in
  `models.py` would then write *local* times into columns holding naive UTC, producing mixed-tz
  data that is unrecoverable after the fact.
- **A per-user timezone preference.** Genuinely foreclosed rather than merely deferred: there is
  one shared admin password and no user table at all (see
  `architecture/02-admin-password-gate.md`). There is no "user" to hang a preference on.
- **`pytz` or `python-dateutil`.** Unnecessary. `zoneinfo` is stdlib from 3.9 and the container
  is 3.11.16.

## Decision

**Storage stays naive UTC. A single `DISPLAY_TIMEZONE` setting (an IANA zone name, default
`UTC`) is applied only when a value is rendered, or when a local calendar day is the thing
being decided.** Never convert before storing.

Mechanically:

- `dashboard_app/app/utils/timezone_utils.py` owns the conversion. It is deliberately
  Flask-free so `execution/` scripts can import it without an app context.
- Templates render through the `|localtime` Jinja filter, never `.strftime()` on a stored value.
- The UTC path short-circuits to stdlib `datetime.timezone.utc` and never constructs
  `ZoneInfo("UTC")`, because that *also* raises when the tz database is absent. The default
  configuration is therefore structurally immune to a missing tzdata.
- An unresolvable zone logs an ERROR once at startup and degrades to UTC. A display setting must
  never be able to prevent the dashboard from booting.

🔴 **Carve-out that must not be unified:** `execution/github_sync.py` writes its `last_polled`
cursor as a UTC ISO-8601 string and compares it against GitHub's own UTC `updatedAt` with a
plain **lexicographic string comparison**. That is a wire-protocol value, not a display value.
Making it local-tz would still compare "successfully" and silently return the wrong polling
window — no exception, no log, just missed or duplicated issues. It stays UTC unconditionally.

## Consequences

**Easier.** One knob changes every rendered timestamp. The storage layer is untouched, so there
is no migration and no risk to existing rows. `DISPLAY_TIMEZONE` defaults to `UTC`, which makes
the conversion an identity — the change is a no-op for anyone who does not set it, and all 11
pre-existing repetition tests pass byte-identically.

**Harder / accepted downsides.**

- The setting is global. Two operators in different zones cannot each see their own local time,
  and the architecture above means that is not a small fix.
- `DISPLAY_TIMEZONE` also governs the Repeat_\* reset boundary, which is business logic rather
  than display. `LOCAL_TIMEZONE` would have named that more accurately; one knob was judged
  worth the slightly wrong name, since the referent is identical — the operator's local day is
  both what they read and what "daily" means to them. The mismatch is called out explicitly in
  `.env.example` and `domains/business_logic.md`.
- **"Joined At" dates visibly change** for any Employee created between 00:00–04:00 UTC: they
  shift back one calendar day. This is correct, but it looks like data corruption if unexpected.
- Changing the value requires `docker compose up -d --force-recreate <service>`. A plain
  `docker restart` reuses the environment frozen at container creation and will **not** pick it
  up — `env_file` is resolved by compose at creation time.

**Follow-up this created.** `tzdata` was added explicitly to the `Dockerfile`'s apt line: it is
present today only because `python:3.11-slim` resolves to Debian 13 (trixie), which pulls it in
transitively, so a base-image bump could otherwise remove it silently. `tests/test_timezone.py`
was added (18 tests, DB-free). `tests/test_repetitions.py` and `tests/test_edge_cases.py` were
pinned to `DISPLAY_TIMEZONE=UTC` so their assertions cannot depend on ambient container env —
required, not cosmetic: their midnight `updated_at` values are exactly what flips under a
negative-offset zone.

**Explicitly not done.** `TimestampMixin` still uses `datetime.utcnow`, deprecated as of Python
3.12. The container is 3.11.16 so nothing breaks yet, but when it is migrated the replacement is
`datetime.now(timezone.utc).replace(tzinfo=None)` — **the naive-UTC storage convention must be
preserved**, so that nobody "modernizes" six models into mixed-tz data.
