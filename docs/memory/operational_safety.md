# Operational Safety — What an Agent May Do Unsupervised

## Unsupervised (no confirmation needed)

- Any data operation via `execution/agent_actions.py`, **including deletes** and their cascade
  effects (`delete_system` → its Projects → their Tasks; `delete_project` → its Tasks). See
  `governance/02-confirmation-policy.md`.
- Editing source code for a system change, then `docker cp`-ing it into the running container to
  make it testable.
- Running a database migration (`flask db upgrade`) — but see the hard-to-reverse exception below.
- Reading GitHub state via `execution/github_sync.py`'s read-only GraphQL calls.

## Needs the user

- **Restarting a container** (`docker restart ...`) to verify a system change — Claude Code never
  does this itself; it syncs the file and gives the user the exact command. See
  `governance/01-development-workflow.md`.
- **Writing to GitHub in any form** — never allowed, regardless of who asks or how. See
  `architecture/01-github-readonly-guardrail.md`. This is not a "needs confirmation" case, it's an
  absolute prohibition with no override.
- Anything git-destructive (`push --force`, `reset --hard`, discarding uncommitted work) or
  committing without being explicitly asked.
- A schema migration or any other **hard-to-reverse** change to the live database — take a backup
  first (e.g. via SQLite's own backup API, not a raw file copy while WAL-mode writes may be
  in-flight) before running it, the same way
  [ADR 0001](../adr/0001-system-project-task-hierarchy.md)'s migration did.
