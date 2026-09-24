# API Endpoints — Route Index

Every `@bp.route` in `dashboard_app/app/main/routes.py`. This is a scan index, not a contract —
these are server-rendered HTML/HTMX-partial routes for the dashboard itself, not an external API
(see `api/README.md`). Keep this in sync with `routes.py` in the same change that adds/removes a
route.

## Pages (full HTML)

| Method | Path | Function | Renders |
|---|---|---|---|
| GET | `/` | `index` | `index.html` — dashboard home, analytics cards + Projects table + Notification History panel (dashboard-only, see `business_logic.md`'s `Notification` entity) |
| GET | `/employees` | `employees_list` | `employees.html` — Team table |
| GET | `/projects` | `projects_list` | `projects.html` — flat, org-agnostic Projects list |
| GET | `/systems` | `systems_list` | `systems.html` — Systems (GitHub orgs) list |
| GET | `/systems/` | `systems_list_slash` | redirects to `/systems` |
| GET | `/system/<int:system_id>` | `system_detail` | `system_detail.html` — one System's Projects |
| POST | `/login` | `login` | verifies `ADMIN_PASSWORD` (see `architecture/02-admin-password-gate.md`), sets `session['authenticated']`, redirects to `next` or `/` |
| GET | `/tasks` | `tasks_list` | `tasks.html` — global Tasks table. Query-string filters `f_system_id`/`f_project_id`/`f_employee_id`/`f_q` are honored on this initial load (e.g. linked from a Project/Team-member name, or a Notification History entry — see `flows.md`); `f_status` is still HTMX-only — it only takes effect once the filter row fires a request against `/api/updates/tasks`, not on a fresh page load |

## Partial refresh endpoints (`/api/updates/*`, HTMX/SSE-driven)

| Method | Path | Function | Used by |
|---|---|---|---|
| GET | `/api/updates/index` | `api_index_updates` | dashboard analytics cards, on `sse:datachanged` |
| GET | `/api/updates/employees` | `api_employees_updates` | Team table |
| GET | `/api/updates/projects` | `api_projects_updates` | Projects table (both `/` and `/projects` share it) |
| GET | `/api/updates/systems` | `api_systems_updates` | Systems table |
| GET | `/api/updates/system/<int:system_id>` | `api_system_detail_updates` | one System's Projects sub-table |
| GET | `/api/updates/tasks` | `api_tasks_updates` | Tasks table body, respects all active filters |
| GET | `/api/updates/notifications` | `api_notifications_updates` | Notification History panel (dashboard-only) |

## Mutations (state-changing, `POST`)

| Method | Path | Function | Effect |
|---|---|---|---|
| POST | `/update-task/<int:task_id>` | `update_task_status` | status/assignee/project change from a Tasks-table row dropdown; returns the refreshed Tasks partial |
| POST | `/update-project/<int:project_id>` | `update_project_status` | status change from a Projects-table or System-detail row dropdown; `?refresh=system` returns the System-detail partial instead of the flat Projects one |
| POST | `/agent/chat` | `agent_chat` | the HUD chat/voice entrypoint — persists the message, calls the Orchestrator, returns the AI's reply partial plus any `HX-Trigger` navigation/alert |
| POST | `/notifications/<int:notification_id>/delete` | `delete_notification` | dismisses one Notification History entry; returns `('', 200)` — an htmx `hx-swap="outerHTML swap:300ms"` drives the slide-out animation, and htmx never swaps a `204`, so this must stay `200` |
| POST | `/notifications/delete-all` | `delete_all_notifications` | clears the **whole** Notification History in one request. Returns the re-rendered `partials/_notifications_panel.html` (not `('', 200)` — with every row gone there is no single `.notification-item` left to animate out, so the caller swaps the whole card), plus an `HX-Trigger: vision-alert` toast. Deliberately does *not* `record_notification()` its own action — see `flows.md` |

## Internal / infrastructure

| Method | Path | Function | Purpose |
|---|---|---|---|
| GET | `/stream` | `stream` | the SSE event stream every page subscribes to |
| POST | `/internal/notify-update` | `notify_update` | fire-and-forget target for `trigger_ui_refresh()` — fans the message out over SSE (`sse:datachanged`, and `sse:toast` if a toast payload is included) |

Not HTTP routes, but Flask CLI commands in the same app (`dashboard_app/app/commands.py`): `flask
seed` (populates test data) and `flask process-repetitions` (manually runs
`execution/repetition_processor.py`'s reset logic once; its reset boundary is the local calendar day in `DISPLAY_TIMEZONE`, see `business_logic.md`).
