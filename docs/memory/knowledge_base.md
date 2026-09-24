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

## Timestamps and ordering

- **`Task.created_at` is NOT a proxy for when its GitHub issue was created**, and reaching for it
  as an ordering key is a trap that looks correct. Measured 2026-09-09: 206 of 306 rows were
  inserted in bulk sync batches — 102 inside the single minute `2026-08-24 10:34`, five within
  17 *milliseconds* on 2026-09-03 — and within a batch the insertion order is GitHub's
  `updatedAt DESC` at sync time, frozen forever. Concrete inversion: task 301 (issue #22) was
  inserted before task 302 (issue #21). Order by `Task.github_created_at` (GitHub's own
  `issue.createdAt`) instead; `domains/business_logic.md` has the full rule.
- **`datetime.min.timestamp()` raises `ValueError` on Linux** (year 1 is out of range), so it is
  not usable as a sort sentinel. Comparing `datetime` objects *directly* is always safe — only
  the conversion to a POSIX timestamp is not. Use a fixed real sentinel like
  `datetime(1970, 1, 1)` and never negate a datetime; to sort one field ascending and another
  descending, run two stable `sorted()` passes rather than building a signed composite key.
- **Mixing naive and tz-aware datetimes in one sort key raises `TypeError` mid-sort.** In a
  request path that means a 500 on the whole page, from a single stray value. Normalize inside
  the comparison key, not only at the write boundary — the write boundary can be bypassed by a
  future migration or a caller that skips the parser.
- **`ZoneInfo("UTC")` also raises when the tz database is missing**, so a "fall back to UTC"
  handler that constructs it is not actually a fallback. Short-circuit the UTC path to stdlib
  `datetime.timezone.utc`, which needs no tzdata at all.

## GitHub sync

- A closed-unmerged PR drops out of GraphQL's `closedByPullRequestsReferences` connection on an
  issue — that field only tracks PRs that are still open or that actually closed the issue via
  merge. Detecting an *abandoned* PR (closed without merging) requires
  `timelineItems(itemTypes: [CROSS_REFERENCED_EVENT])` instead, reading each event's
  `source { ... on PullRequest { state merged } }`. See `domains/business_logic.md`'s auto-status
  rules and `_abandoned_pr_refs` in `execution/github_sync.py`.
- **A Task's `employee_id` is a projection of GitHub, not locally editable state.** Both sync
  passes (`sync_once` and `sync_active_tasks_once`) pass `employee_id` to `update_task`
  *unconditionally* — `employee_id if employee_id is not None else 0` — so a manually-set assignee
  is overwritten on the next cycle (within 5s for an `In-Progress`/`Testing` Task) by whatever the
  issue's GitHub assignees say (the rule itself is in `domains/business_logic.md`'s auto-status
  section; this is its operational consequence). Setting an assignee locally only sticks where
  GitHub already agrees — or where the Project is `Blocked` (see next entry). **So "assign this
  task to X" is not something this project can honour for a GitHub-linked Task**: reassign the
  issue on GitHub instead, which this project may never do itself (see
  `architecture/01-github-readonly-guardrail.md`).
- **A `Blocked` Project is invisible to both sync passes, silently.** `sync_once` and
  `sync_active_tasks_once` both filter `Project.status != StatusEnum.BLOCKED`, so a Blocked
  Project's Tasks are never reconciled *and* its new issues are never discovered — the board keeps
  showing stale assignees/statuses and simply omits issues opened since the Project was blocked,
  with nothing in the logs to say so. Verified 2026-09-03: a real Project was Blocked,
  so issues #116/#117/#119 existed on GitHub with no Task at all, and #112/#113/#114 still showed a
  previous assignee weeks after being reassigned. Before trusting a Blocked Project's Tasks, query
  GitHub directly (`fetch_issues_by_number`, read-only) rather than reading the local rows.
- **Manually setting a Task to `In-Progress` is durable; `Todo` is not reachable manually.**
  `_should_auto_update` never regresses an open issue's Task back to `Todo`
  (`current == IN_PROGRESS` returns `computed != TODO`), so a hand-set `In-Progress` survives the
  5s recheck for an issue with no PR. It will still advance on its own to `Testing` once a PR is
  linked, and `DONE`/`BLOCKED` always win — even over a manually-set status.
- A `closedByPullRequestsReferences` node is already a full `PullRequest` object, not just
  `{number, state}` — `reviews(last:, states:)` and `commits(last:)` are valid sub-selections on
  it, so fetching PR review/commit data needs **no second GraphQL request**, just a wider field
  selection on the same query. Used to compute `Task.github_review_state` (see
  `domains/business_logic.md`'s "Review-state rule"). When deriving anything from a `reviews`
  connection, always dedupe to each author's *latest* submission first — GitHub never mutates an
  earlier review's `state` when the same author submits a later one.
