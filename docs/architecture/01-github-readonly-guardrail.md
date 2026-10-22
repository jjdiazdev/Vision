# Guardrail: GitHub Integration Is Read-Only, Permanently, No Exceptions

The `github-sync` job (`execution/github_sync.py`, `execution/github_sync_worker.py`, the
`github-sync` service in `docker-compose.yml`) and any other code in this project that talks to
the GitHub API has one absolute, non-negotiable limit: **it only ever reads GitHub state — it
never writes, modifies, or deletes anything there.**

This applies identically to **every polling cadence** — this is not a rule for only one speed:

- `sync_once` — the slow, full discovery/reconciliation pass (every `DISCOVERY_INTERVAL_SECONDS`,
  60s by default).
- `sync_active_tasks_once` — the fast recheck of `In-Progress`/`Testing` Tasks (every
  `SYNC_INTERVAL_SECONDS`, 5s by default).
- `sync_plan_once` (`execution/plan_sync.py`) — the live PR/CI/review state of the active
  implementation plans' issues (every `PLAN_SYNC_INTERVAL_SECONDS`, 15s by default).

The rate-limit check that gates all cadences (`get_rate_limit()`) is only actually invoked at the
slow cadence; if remaining budget drops below `RATE_LIMIT_SAFETY_THRESHOLD` (50 points,
`execution/github_sync_worker.py`), all cadences pause until the next scheduled discovery check.

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
`update_task`, `create_employee`), or — for plan items only — directly into `PlanItem`'s live
columns (`execution/plan_sync.py`), which are local display state with no GitHub counterpart.
The plan query reads issue `state`/`stateReason` and, per linked PR, `title`, `headRefName`,
`isDraft`, `merged`, `reviewDecision`, `repository.nameWithOwner`, `closingIssuesReferences` and
the last commit's `statusCheckRollup.state`. Projects (repos) are managed manually ahead of time —
`github_sync` never creates them, it only syncs Tasks inside Projects that already have
`github_repo` configured. GitHub never receives a write originated from this project.

## Token scope

`GITHUB_TOKEN` must have **Read-only** permissions exclusively (Contents, Metadata, Issues, Pull
requests, Commit statuses) and zero write permissions. Commit statuses is what lets the plan
graph show a red CI; without it `statusCheckRollup` reads `null` and the graph simply never shows
a PR as failing CI (it still shows changes requested). If a future task appears to need a GitHub
write permission, that is a signal the task is out of scope for this guardrail — it gets dropped
or reframed, the permission does not get enabled.

## Enforcement in code

Since 2026-10-22 the rule is also enforced, not only documented: every GitHub request goes
through `execution/github_sync.py::graphql_query`, which calls `assert_read_only` first. That
function strips strings and comments from the GraphQL document and raises `GitHubWriteAttempt`
— before any network call — if a `mutation` or `subscription` operation appears at the top
level. `requests.post` to `api.github.com` appears nowhere else (the POST is just how GraphQL
queries travel). Tests: `tests/test_plan_status.py::TestReadOnlyGuard`. The token's read-only
scope remains the second, independent layer.

## For any new code

Any new code added to talk to the GitHub API (REST or GraphQL) must stay inside this limit: reads
only, never `POST`/`PATCH`/`PUT`/`DELETE` or a mutation against a GitHub resource. GraphQL calls
go through `graphql_query`; never call `requests.post` against GitHub directly. A REST read, if
one is ever needed, gets its own GET-only helper next to it — not a bypass.
