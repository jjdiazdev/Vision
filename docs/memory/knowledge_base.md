# Knowledge Base

Durable, established facts and patterns already in use — consult before introducing a new
pattern, so the codebase reuses instead of reinventing.

## Orchestrator

- **Loop constraints**: `orchestrator/brain.py` uses a `max_iterations` limit to prevent infinite
  loops during tool chaining. Currently **30** (verified directly in code 2026-08-27 — an earlier
  note here said 50, and `domains/system_architecture.md`'s predecessor doc said 8; neither was
  current. Always re-check this value in code rather than trusting a doc, it has drifted before).

## SSE / real-time sync

- `trigger_ui_refresh()` (duplicated identically in `execution/agent_actions.py` and
  `execution/log_progress.py`) posts to three URLs (`127.0.0.1:5000`, `127.0.0.1:5001`, `web:5000`)
  so it works whether called from the host, inside the `web` container, or from the separate
  `github-sync` container. See `domains/flows.md`.

## Toasts

- The one true choke point for anything that needs to see *every* toast (e.g. a sound, a badge
  counter) is the `@vision-alert.window` Alpine handler in `base.html` — **not**
  `window.addAlert()`. There are two independent ways a toast gets dispatched (SSE-driven
  `trigger_ui_refresh(toast=...)` calls and direct client calls, vs. an `HX-Trigger: vision-alert`
  header set directly by a few routes), and only `@vision-alert.window` sees both. See
  `domains/flows.md`'s toast-mechanism section for the full inventory.
- Any `update_*` function in `execution/agent_actions.py` must diff old vs. new values and only call
  `trigger_ui_refresh(toast=...)` when something actually changed (a `changed` flag) — never
  unconditionally. Without this, a caller that re-sends the same values (e.g. `github_sync.py`'s
  5-second active-task recheck) produces a phantom toast on every call. `create_*`/`delete_*` don't
  need this — there's no no-op case for them.
- A `POST` route driving an htmx delete-with-animation (`hx-swap="outerHTML swap:N"` +
  `.htmx-swapping` CSS transition) must return `('', 200)`, never `204` — htmx's hard rule is that a
  `204` response is *never* swapped regardless of `hx-swap`/target, so copying a nearby `{}, 204`
  "nothing to render" idiom here silently makes the delete a no-op with no error. See the
  Notification-dismiss route (`domains/flows.md`) for the concrete case this bit.
- A fixed-height, internally-scrolling card needs `min-height: 0` on **every** intermediate flex-column
  wrapper between the fixed-height ancestor and the `overflow-y:auto` scrolling element — nested flex
  columns default to `min-height: auto`, which lets the wrapper grow to fit its content instead of
  respecting the ancestor's height, silently defeating the scroll. `.hud-chat-window`/`.hud-chat-body`
  works with no extra rule because it's a *direct* parent→child pair; the dashboard Projects/
  Notification cards needed one more `min-height:0` rule specifically because `_projects_table.html`
  has an extra unstyled `<div>` in between.
- **Never leave a bare `hx-swap`/`hx-target` on an element that also contains an unrelated,
  `hx-boost`-navigable link** — `hx-boost` inherits both attributes from the closest ancestor that
  declares them, same as an explicit `hx-get`/`hx-post` would. A `hx-swap="outerHTML swap:Nms"` meant
  only for a sibling delete button leaked onto a plain `<a href>` inside the same card this way,
  causing the link's boosted navigation to `outerHTML`-swap `#slot` itself (the app's global nav
  target) instead of its contents — which silently broke every other HUD nav button afterward, since
  their target element no longer existed. If a container needs `hx-swap` for one specific descendant's
  request, put the attribute on that descendant (or an ancestor scoped tightly enough), not on a wider
  wrapper that also contains unrelated links. See `domains/flows.md`'s Notification History section.

## GitHub sync

- A closed-unmerged PR drops out of GraphQL's `closedByPullRequestsReferences` connection on an
  issue — that field only tracks PRs that are still open or that actually closed the issue via
  merge. Detecting an *abandoned* PR (closed without merging) requires
  `timelineItems(itemTypes: [CROSS_REFERENCED_EVENT])` instead, reading each event's
  `source { ... on PullRequest { state merged } }`. See `domains/business_logic.md`'s auto-status
  rules and `_abandoned_pr_refs` in `execution/github_sync.py`.
- A `closedByPullRequestsReferences` node is already a full `PullRequest` object, not just
  `{number, state}` — `reviews(last:, states:)` and `commits(last:)` are valid sub-selections on
  it, so fetching PR review/commit data needs **no second GraphQL request**, just a wider field
  selection on the same query. Used to compute `Task.github_review_state` (see
  `domains/business_logic.md`'s "Review-state rule"). When deriving anything from a `reviews`
  connection, always dedupe to each author's *latest* submission first — GitHub never mutates an
  earlier review's `state` when the same author submits a later one.
