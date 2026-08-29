# Admin Password Gate

A single shared password protects the whole dashboard — distinct from the multi-tenant auth/RBAC
already on the roadmap (`docs/01-roadmap.md`'s Phase 7.2, not built). There is no `User` table, no
per-person accounts: everyone who knows the one password gets full access, matching this app's
current status as a single-tenant internal tool (`docs/00-overview.md`).

## How it works

- `ADMIN_PASSWORD` (`.env`) holds a **Werkzeug password hash** (`werkzeug.security.generate_password_hash`
  output), not a plaintext password. Generate one with:
  ```
  python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('yourpassword'))"
  ```
- `POST /login` (`dashboard_app/app/main/routes.py::login`) verifies the submitted password with
  `check_password_hash(ADMIN_PASSWORD, submitted)` and, on success, sets `session['authenticated'] = True`.
- A `@bp.before_request` hook (`require_admin_auth`, same file) enforces this on every route in the
  `main` blueprint, **default-deny**: anything not explicitly exempted requires
  `session.get('authenticated')`. A normal page GET without a valid session gets `lock.html` rendered
  in place of the real page (no DB queries run — the real view function is never called); an
  API/action-style request (`/api/updates/*`, `/stream`, `/agent/chat`, any non-GET) gets a plain `401`.
- **Exemptions**: `main.login` (or nobody could ever submit the password) and
  `main.notify_update` (`POST /internal/notify-update`) — the latter is called server-to-server, over
  loopback, by `trigger_ui_refresh()` in `execution/agent_actions.py`/`execution/github_sync.py`
  (see `docs/domains/flows.md`'s SSE flow) with no browser session cookie at all. Gating it would break
  the entire live-update pipeline app-wide, not just for locked visitors.
- **Resets on browser close by design, not by extra code**: `session.permanent` is never set to `True`
  anywhere in this app, and Flask's own default for that is `False` — so `session['authenticated']`
  already lives in a plain browser-session cookie that the browser discards when it fully closes.

## Operational gotcha: escape `$` in `.env`

A Werkzeug hash always contains literal `$` separators (e.g. `scrypt:32768:8:1$salt$hash`).
docker-compose treats `$word` inside `.env` as a variable reference and, if that "variable" isn't
set, silently substitutes an empty string — printing `WARN ... variable is not set. Defaulting to a
blank string.` and corrupting the value that actually reaches the container. The symptom is exactly
"the correct password never works, with no error" (login always fails, `check_password_hash` sees a
mangled hash). **Fix**: double every `$` to `$$` in `.env`'s `ADMIN_PASSWORD` line before pasting the
generated hash. This corrupts the value in place — a container already started with the bad value
needs `docker-compose up -d` (recreate), not just `docker restart`, to pick up the corrected one.

## Known limitations (deliberate, not oversights)

- **No brute-force rate-limiting or lockout** on repeated failed `/login` attempts. Not implemented —
  wasn't asked for, and this is a single shared password behind what's currently a single-tenant
  internal tool, not a public-facing login.
- **The gate's real strength depends on `SECRET_KEY` being a genuine secret.** `dashboard_app/config.py`
  falls back to a hardcoded `'dev-secret-key'` if `.env` doesn't set one. Flask signs (doesn't encrypt)
  the session cookie with this key — if it's left at the checked-into-git fallback, anyone who has seen
  this repository could forge a valid `session['authenticated'] = True` cookie without ever knowing the
  password. Always set a real, generated `SECRET_KEY` in `.env` before relying on this gate.
