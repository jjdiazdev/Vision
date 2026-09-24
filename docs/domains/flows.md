# Flows — Sync/Notification Wiring and Navigation

## Real-time sync flow (SSE)

Every data mutation — whether from a human clicking a dropdown, the AI Orchestrator, Claude Code
running `agent_actions.py` directly, or the `github-sync` background worker — ends up reflected in
the browser the same way, with no polling and no manual reconciliation step:

1. A mutation function in `execution/agent_actions.py` (or `execution/log_progress.py`) commits
   the change to the shared SQLite DB.
2. It calls `trigger_ui_refresh(message, toast=None)`, which fires a background thread that POSTs
   to `/internal/notify-update` on `127.0.0.1:5000`, `127.0.0.1:5001`, and `web:5000` (the last one
   for cross-container reachability from the `github-sync` container).
3. `notify_update()` (`dashboard_app/app/main/routes.py`) calls `announcer.announce(msg)` — a
   `sse:datachanged` event broadcast to every connected `/stream` subscriber — plus a second
   `sse:toast` event if a `toast` payload (`{"message": ..., "type": "success"|"error"|"info"}`)
   was included, so a background/CLI-driven change produces the identical corner-toast feedback a
   manual UI edit does.
4. Every page's relevant `hx-get`-on-`sse:datachanged` element re-fetches its own
   `/api/updates/*` partial (see `domains/api_endpoints.md`) and HTMX swaps it in.

`dashboard_app/app/main/routes.py`'s `update_task_status()`/`update_project_status()` also call
`trigger_task_update()`/`trigger_project_update()` (`dashboard_app/app/utils/trigger.py`) alongside
the SSE path above; `execution/repetition_processor.py` calls only that pair, not
`trigger_ui_refresh()` — see `governance/03-agent-execution-protocol.md`'s Truth Sync mandate for
why that's a legitimate narrow exception rather than a doc gap.

### Toast mechanism — two independent paths, not one

Both end up as the same `vision-alert` **window** CustomEvent, caught by one Alpine handler
(`@vision-alert.window`, `base.html`) that pushes into the `alerts` array rendered by
`.hud-alerts-container` — but they're dispatched two different ways:

- **Mechanism A (SSE)** — the `trigger_ui_refresh(toast={...})` → `sse:toast` path described above.
  Used by every `agent_actions.py` mutation, since those have no HTTP response of their own to attach
  a header to. Also reached by two direct client-side calls to `window.addAlert(...)`: the "copy name"
  icon (`_employees_table.html`) and `voice.js`'s unsupported-browser fallback.
- **Mechanism B (`HX-Trigger` header)** — `update_task_status()`, `update_project_status()`, and
  `agent_chat()` (on an Orchestrator error) each set an `HX-Trigger: {"vision-alert": {...}}` response
  header directly, **never calling `trigger_ui_refresh`/`window.addAlert`**. This is *separate* from
  those two routes' `.trigger`-file calls mentioned above — one HTTP response can carry both an
  `HX-Trigger` header and have already written a `.trigger` file with no relation between them.

**Toast-trigger inventory** (kept current here — update this table when adding a new toast source):

| Source | Mechanism | Fires on |
|---|---|---|
| `create_system`/`update_system`/`delete_system` | A | Any real change (create/delete always; update only if a field actually changed — see below) |
| `create_project`/`update_project`/`delete_project` | A | Same pattern |
| `create_task`/`update_task`/`delete_task` | A | Same pattern — includes every `github_sync` auto status/review-state/assignee update |
| `create_employee`/`update_employee`/`delete_employee` | A | Same pattern |
| `log_task_progress` (CLI, `execution/log_progress.py`) | A | Always |
| `update_task_status()` manual dropdown | B | Every manual Task edit |
| `update_project_status()` manual dropdown | B | Every manual Project edit |
| `agent_chat()` Orchestrator error | B | LLM/action failure |
| "Copy name" icon (Team view) | A (direct `addAlert`) | Click |
| Speech recognition unsupported (`voice.js`) | A (direct `addAlert`) | Unsupported browser |
| Repeating-Task auto-reset (`execution/repetition_processor.py`) | **None** | Never toasts today — a known, undecided gap, not a bug |

**No-op suppression**: every `update_*` function in `execution/agent_actions.py` diffs each field's
new value against the current one and only calls `trigger_ui_refresh(toast=...)` if something
actually changed (a `changed` flag gates the call) — with **one deliberate carve-out**:
`update_task`'s `github_created_at` branch persists its value but never sets `changed`, because
it is machine-synced metadata with no user action behind it and both sync cadences pass it on
every pass. Setting `changed` there would toast (and play a sound) every five seconds. The
`session.commit()` is unconditional, so the write still lands. This is an exception to the rule,
not a violation of it: the rule exists to suppress meaningless toasts, and that is exactly what
the carve-out does — `create_*`/`delete_*` don't need this, since
creating/deleting is always a real change. This matters because `github_sync.py`'s 5-second
active-task cadence re-sends `update_task()` for every active Task on every cycle whether or not
anything changed; without the diff, that would toast (and play a sound) every 5 seconds regardless.

### Notification History persistence

Every toast above now also persists a `Notification` row (see `business_logic.md`), read by the
Dashboard-only "Notification History" panel (`partials/_notifications_panel.html`):

- **Mechanism A**: persisted *inside* `trigger_ui_refresh()` itself (both the `agent_actions.py` and
  `log_progress.py` copies) — whenever `toast` is truthy, a `Notification` row is written before the
  SSE announce fires, wrapped in its own try/except so a persistence failure can never break the
  existing SSE path. `create_task`/`update_task`/`delete_task`/`log_task_progress` additionally pass
  `employee_id=task.employee_id` through to `trigger_ui_refresh` (captured *before* `session.delete`
  in `delete_task`, since the ORM instance isn't trusted after commit); every other call site leaves
  it `None` (System/Project/Employee have no assignee concept).
- **Mechanism B**: a small `record_notification(message, type='info', employee_id=None)` helper in
  `routes.py`, called directly from `update_task_status()`, `update_project_status()`, and
  `agent_chat()`'s error branch — these never call `trigger_ui_refresh`, so they persist independently,
  riding whichever `db.session.commit()` already exists nearby rather than adding a new one.
- A consequence of centralizing Mechanism A inside `trigger_ui_refresh`: the still-open
  `repetition_processor.py` no-toast gap (row 10 of the inventory above) will start producing
  Notifications automatically, with zero Notification-specific code, whenever that gap is eventually
  closed by giving it a `toast=` argument.
- Dismissal (`POST /notifications/<id>/delete`) **must return `('', 200)`, not `{}, 204`** — htmx
  never swaps a `204` response regardless of `hx-swap`, which would silently make the dismiss button
  a no-op (the nearby `/internal/notify-update` endpoint's `{}, 204` is a different, non-htmx-driven
  caller and isn't a safe pattern to copy here).
- **Clear-all (`POST /notifications/delete-all`)** empties the panel in one request and is the one
  state-changing route in `routes.py` that intentionally skips `record_notification()`: recording
  it would re-populate the list the button exists to empty, leaving a single "history cleared" row
  behind. Feedback is a display-only `HX-Trigger: vision-alert` toast instead, which never
  persists a row (only Mechanism A above persists). It returns the **re-rendered panel**, not
  `('', 200)` — the per-row slide-out has no element left to animate — and announces
  `announcer.announce("clear_notifications")` so other open dashboards refetch and empty too. The
  button is rendered only when `notifications` is non-empty, and declares its own
  `hx-target`/`hx-swap` (never on the `.notifications-header` wrapper) per the inheritance gotcha
  below.
- A Task-related card is a link to `/tasks?f_project_id=...&f_employee_id=...&f_q=...` — the first
  two come from `Notification.task_id`/`project_id`'s snapshot, but `f_q` is built from
  `Notification.task.name` (the **live** relationship, not a stored snapshot) specifically so a
  since-renamed Task is still found by search; `tasks_list()` (`routes.py`) now honors `f_q` on the
  initial page load for this to work (previously `f_q` only worked via the HTMX filter row — see
  `api_endpoints.md`). If the Task no longer exists, `f_q` is simply omitted from the link, which is
  correct here (nothing to search for).
- **htmx-inheritance gotcha this card design already hit once**: the outer `.notification-item` div
  originally carried its own `hx-swap="outerHTML swap:500ms"` (seemingly harmless — the dismiss button
  already declared its own `hx-swap`/`hx-target` and didn't need it). But `hx-boost`-driven navigation
  on any link nested inside inherits `hx-swap`/`hx-target` from the closest ancestor that declares
  them — so clicking the Task link inherited the *dismiss animation's* swap config instead of `#slot`'s
  own `innerHTML transition:true`, causing an `outerHTML` swap of `#slot` itself (replacing the element
  the whole app targets for navigation, not just its contents) and silently breaking every HUD nav
  button afterward. Fixed by removing the redundant attribute from the ancestor and declaring
  `hx-target`/`hx-swap` explicitly on the link itself, matching how `.hud-buttons-container` already
  does. See `knowledge_base.md`.

### Dashboard-only two-column layout pattern

The Notification History panel sits beside the Projects table only on `/` (`index.html`), not on the
dedicated `/projects` view — both pages `{% include %}` the *same* `partials/_projects_table.html`
verbatim, so the height/half-width/scroll treatment is applied by wrapping that include in a new
ancestor (`.dashboard-projects-row` > `.dashboard-projects-col`) in `index.html` only, with all sizing
CSS scoped through a descendant selector rooted at that ancestor (e.g. `.dashboard-projects-col
.projects-table-container { height:100%; ... }`) rather than touching `.projects-table-container`'s
own base rules — `/projects` never matches that ancestor, so it's unaffected. Reuse this same
pattern (new ancestor wrapper + scoped descendant selectors) for any future dashboard-only variant of
an existing shared partial, rather than forking the partial itself.

**Sound**: `window.playToastSound()` (`base.html`, next to `window.addAlert`) plays
`dashboard_app/app/static/sounds/toast-notification.mp3` once per toast. It's called from
`@vision-alert.window` itself — not from inside `window.addAlert` — specifically so it also covers
Mechanism B, which never calls `addAlert`. Wrapped in `.catch(() => {})` so a missing file or a
browser autoplay-policy rejection never breaks the visual toast.

**Correction (this file previously overstated this)**: there **is** still a file-based mechanism —
`trigger_task_update()`/`trigger_project_update()` write a real `.trigger` file to
`.tmp/triggers/task_{id}.trigger`/`project_{id}.trigger` on every one of those calls. What no
longer exists is a *reader*: a repo-wide search turns up zero code anywhere that checks for,
reconciles against, or deletes these files — the old SOP (`.agent/domains/docs/SYNC_SOP.md`,
since replaced) that mandated doing so is what's actually gone, not the write side. In practice
this means `.tmp/triggers/` accumulates files that nothing ever cleans up. See
`governance/03-agent-execution-protocol.md`.

## Navigation flow (`navigate_to` tool)

The Orchestrator (and any agent) can express navigation intent via the `navigate_to` tool
(`execution/agent_actions.py`), which maps a human-readable destination to an internal route name:

| Human term | Internal route |
|---|---|
| home, dashboard | `index` |
| staff, team, employees | `employees` |
| projects, work | `projects` |
| systems, organizations, orgs | `systems` |
| tasks | `tasks` |

- **Return pattern**: `NAVIGATE:{route_name}`.
- Dynamic destinations use a `type:ID` pattern, resolved in `agent_chat()`
  (`dashboard_app/app/main/routes.py`): `system:5` → `/system/5`, `project:5` → `/tasks?f_project_id=5`
  (clicking/navigating to "a project" opens the Tasks view pre-filtered to it — there's no
  standalone project-detail page anymore, see `api_endpoints.md`).
- `agent_chat()` sets an `HX-Trigger: {"vision-navigation": {"target": url}}` header; the frontend
  (Alpine.js, `base.html`) listens for it and performs the HTMX swap.

### CLI usage

```bash
docker exec vision-web-1 python -m execution.agent_actions navigate --to "systems"
```

## Mobile UX

For viewports narrower than 470px, `#vision-viewport` (`base.html`) gets a `rotate(90deg)` CSS
transform, forcing a landscape layout regardless of physical device orientation — verified current
in `dashboard_app/app/static/css/style.css`. When the chat opens on a narrow viewport, the native
OS keyboard is suppressed and the screen splits: chat window (55%, left) and a custom rotated
virtual keyboard (45%, right). The exact suppression condition (`base.html`) is
`(window.innerWidth <= 470 || isLandscape) && !useSystemKeyboard` — it also triggers on an actual
landscape orientation regardless of width, and has a `useSystemKeyboard` escape hatch, not just the
narrow-viewport case this paragraph's first sentence describes.
