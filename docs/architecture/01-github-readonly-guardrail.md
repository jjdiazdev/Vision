# Guardrail: GitHub Integration Is Read-Only, Permanently, No Exceptions

The `github-sync` job (`execution/github_sync.py`, `execution/github_sync_worker.py`, the
`github-sync` service in `docker-compose.yml`) and any other code in this project that talks to
the GitHub API has one absolute, non-negotiable limit: **it only ever reads GitHub state — it
never writes, modifies, or deletes anything there.**

This applies identically to **both polling cadences** — this is not a rule for only one speed:

- `sync_once` — the slow, full discovery/reconciliation pass (every `DISCOVERY_INTERVAL_SECONDS`,
  60s by default).
- `sync_active_tasks_once` — the fast recheck of `In-Progress`/`Testing` Tasks (every
  `SYNC_INTERVAL_SECONDS`, 5s by default).

The rate-limit check that gates both cadences (`get_rate_limit()`) is only actually invoked at the
slow cadence; if remaining budget drops below `RATE_LIMIT_SAFETY_THRESHOLD` (50 points,
`execution/github_sync_worker.py`), both cadences pause until the next scheduled discovery check.

## What is permanently prohibited, even if explicitly requested

Creating, editing, closing, reopening, or commenting on issues/PRs; merging; deleting branches,
repos, labels, or native GitHub milestones; modifying files via the API; changing repository or
organization settings; or any other mutation against a GitHub resource. If this is ever requested,
the answer is to explain this guardrail and point the user to do it themselves directly on
GitHub — never a "special mode," never a confirmation prompt to bypass it.

## The one permitted data flow

One direction only: **read** issue/PR state from GitHub (GraphQL, queries only —
`repository { issues }`, `issue(number:)`, `rateLimit` — never mutations) → **reflect** that state
into V.I.S.I.O.N.'s local database through `execution/agent_actions.py` (`create_task`,
`update_task`, `create_employee`). Projects (repos) are managed manually ahead of time —
`github_sync` never creates them, it only syncs Tasks inside Projects that already have
`github_repo` configured. GitHub never receives a write originated from this project.

## Token scope

`GITHUB_TOKEN` must have **Read-only** permissions exclusively (Contents, Metadata, Issues, Pull
requests, Commit statuses) and zero write permissions. If a future task appears to need a GitHub
write permission, that is a signal the task is out of scope for this guardrail — it gets dropped
or reframed, the permission does not get enabled.

## For any new code

Any new code added to talk to the GitHub API (REST or GraphQL) must stay inside this limit: reads
only, never `POST`/`PATCH`/`PUT`/`DELETE` or a mutation against a GitHub resource.
