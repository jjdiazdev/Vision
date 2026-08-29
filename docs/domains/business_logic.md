# Business Logic — Domain Model & Rules

Schema for `dashboard_app/app/models.py`, using SQLAlchemy as the ORM over a single SQLite
database (WAL mode, for concurrent access by the Flask process and the `github-sync` worker).
See [ADR 0001](../adr/0001-system-project-task-hierarchy.md) for why this hierarchy replaced the
earlier Project→Process→Task one.

## Entity-Relationship Diagram

```mermaid
erDiagram
    EMPLOYEE ||--o{ TASK : assigned_to
    SYSTEM ||--o{ PROJECT : contains
    PROJECT ||--o{ TASK : contains

    EMPLOYEE {
        int id
        string name
        datetime created_at
    }

    SYSTEM {
        int id
        string name
        string github_org
    }

    PROJECT {
        int id
        string name
        enum status
        string github_repo
        int system_id
    }

    TASK {
        int id
        string name
        enum status
        int project_id
        int employee_id
        int github_issue_number
        int github_pr_number
        enum github_review_state
    }

    NOTIFICATION {
        int id
        string message
        string type
        int employee_id
        datetime created_at
    }
    EMPLOYEE ||--o{ NOTIFICATION : linked_to
```

## Entities

- **Employee**: represents system and human agents. No status field.
- **System**: a GitHub organization (e.g. "Acme") that owns one or more Projects. `github_org`
  is nullable — a System can exist without a linked org. `Project.system_id` is auto-derived from
  the owner portion of `github_repo` on create/update unless explicitly set (see
  `execution/agent_actions.py::_resolve_system_id`).
- **Project**: a GitHub repository — the mid-level container for work. `github_repo` and
  `system_id` are both nullable (a manually-created Project needn't be GitHub-linked). Deleting a
  System cascades to its Projects; deleting a Project cascades to its Tasks.
- **Task**: the atomic unit of work, assigned to at most one Employee, belonging to exactly one
  Project. `github_issue_number`/`github_pr_number` are nullable and populated by `github_sync`.
  `github_review_state` is likewise nullable, populated only by the fast/active-task cadence (see
  "Auto-status rules" below), and driven by `ReviewStateEnum` (`Changes Requested`,
  `Changes Applied`).
- **Notification**: a persisted record of every toast the dashboard has ever shown — the Dashboard's
  "Notification History" panel reads from this table. `type` mirrors the toast type (`success`/
  `error`/`info`). `employee_id` is nullable and only ever set for Task-related events (the Task's
  assignee at the time) — System/Project/Employee-entity notifications carry no employee, since
  those entities have no assignee concept. Populated from *both* toast-dispatch mechanisms — see
  `domains/flows.md`'s toast-mechanism section. No retention/cleanup policy (same accepted gap as
  `ChatMessage`); the Dashboard query caps display at the 200 most recent rows.

## Computed properties (not columns — `models.py`)

- `Project.progress` — `%` of the Project's Tasks with `status == Done`, 0 if it has none.
- `Project.is_complete` — `True` iff the Project has at least one Task and every Task is `Done`;
  drives the completed-row strikethrough styling in the Projects and System-detail tables.
- `Task.github_url` — the task-name link target: the linked PR's URL if `github_pr_number` is set,
  else the linked issue's URL if `github_issue_number` is set, else `None`. PR takes priority over
  issue when both exist.
- `Task.github_issue_url` / `Task.github_pr_url` — the same two links individually, used by the
  Tasks table's separate Issue/PR columns.
- `Task.review_state_class` — maps `github_review_state` to a CSS class name
  (`task-title-changes-requested` / `task-title-changes-applied` / `None`) for the Tasks table's
  title-color styling. Exists specifically so the template never interpolates the enum's raw,
  space-containing value into a `class="..."` attribute (which would silently produce two broken
  class tokens, the same latent trap `StatusEnum`'s `"Repeat Daily"`-style values have for badges).

## `StatusEnum`

`Todo`, `In-Progress`, `Testing`, `Done`, `Blocked`, `Repeat Daily`, `Repeat Weekly`,
`Repeat Monthly`. Shared across Project and Task, except the three `Repeat_*` values, which are
reserved for Tasks only and filtered out of Project status dropdowns —
`execution/repetition_processor.py` resets a repeating Task back to `Todo` on the appropriate
cadence (daily; weekly on Monday; monthly on the 1st), each time its `updated_at` predates the
reset boundary.

## Auto-status rules (`execution/github_sync.py`)

This is the business logic governing how a Task's status gets computed from live GitHub state —
see that module's own docstring for the authoritative, always-current version; summarized here:

- A **still-open issue** updates Todo/Testing/Done Tasks freely. An **In-Progress** Task only ever
  advances forward (to Testing once a PR is linked, to Done once it's merged) — never regressed
  back to Todo, since a human already claimed it. A **Blocked** Task is left alone by this weaker
  signal.
- A **closed issue** is the highest-priority signal and overrides *any* current status, including
  a manually-set Blocked: closed issue + a closed/merged PR → `Done`; closed issue with no
  completed PR → `Blocked`.
- Same top priority even while the issue is still **open**: if its only related PR(s) were closed
  without merging (abandoned), that's `Blocked` too. GitHub drops a closed-unmerged PR from the
  `closedByPullRequestsReferences` connection, so this specific case is detected via a separate
  `timelineItems` (`CROSS_REFERENCED_EVENT`) query instead — see `_abandoned_pr_refs`.
- Any `Repeat_*` status is always left untouched by sync.
- Employee assignment is always overwritten to mirror GitHub's current single-assignee resolution
  (0 or 2+ assignees → unassigned).

### Review-state rule (`github_review_state`, active-task cadence only)

Unlike the status rules above (which run on both the 60s discovery pass and the 5s active-task
pass), this sub-rule runs **only** on `sync_active_tasks_once` — a Todo Task with a PR under
review is intentionally never colored; it only starts getting checked once it's In-Progress or
Testing. This is why `fetch_issues_by_number`'s query is parameterized by `fields`: the active-task
pass asks for `ISSUE_FIELDS_WITH_REVIEW` (adds `reviews`/`commits` under each PR ref), while the
discovery pass keeps the original, cheaper `ISSUE_FIELDS`.

- Reviews are deduped to each author's **latest** submission first — GitHub never mutates an
  earlier review's `state` when the same author submits a later one, so without this a reviewer
  who requested changes and later approved would still read as "outstanding."
- If any author's latest review is `CHANGES_REQUESTED`, `github_review_state` is set to
  `CHANGES_REQUESTED` — unless the PR's latest commit landed *after* that review's `submittedAt`,
  in which case it's `CHANGES_APPLIED` instead (`_compute_review_state`).
- With no outstanding `CHANGES_REQUESTED` review, it's cleared to `NULL`.
- It's unconditionally cleared to `NULL` the moment a Task's computed status becomes `Done` or
  `Blocked` — necessary because `sync_active_tasks_once` never revisits a Task once it leaves
  In-Progress/Testing, so this is the only chance to clear it via sync.
- A **manual** status change via the Tasks-table dropdown (`update_task_status` in
  `dashboard_app/app/main/routes.py`, which writes `Task.status` directly and bypasses
  `agent_actions.update_task`) also clears `github_review_state` when the new status isn't
  In-Progress/Testing — otherwise a human-driven status change would orphan a stale title color
  that sync would never revisit either.
- "Merged" here matches the existing merge-detection behavior exactly (any merged linked PR, via
  `state == MERGED`) — there is no base-branch-specific ("must be `main`") check, consistent with
  how `_compute_status` has never had one.

## Task list ordering and visibility

- `sort_tasks()` (`dashboard_app/app/main/routes.py`) orders the Tasks table as: **Testing → 
  In-Progress → Todo → Repeat_\* → Done → Blocked**.
- Every Tasks-view query (`tasks_list`, `api_tasks_updates`, and `update_task_status`'s
  tasks-refresh branch) unconditionally excludes Tasks whose Project has `status == Blocked`
  (`Task.query.join(Project).filter(Project.status != StatusEnum.BLOCKED)`, all three sites in
  `dashboard_app/app/main/routes.py`) — since a Blocked Project is also excluded from `github_sync`
  polling (`Project.status != StatusEnum.BLOCKED` in both `sync_once` and `sync_active_tasks_once`'s
  own project-query filters, `execution/github_sync.py`), those Tasks' local status can go stale,
  so they're hidden rather than shown out of date.
