# Agent Execution Protocol

This merges and corrects the old `directives/00_SYSTEM_RULES.md` and `GEMINI.md` — both described
an aspirational `.agent/rules/` structure that was never actually built, and one mandate
(checking `.tmp/triggers/` files before acting) describes a *reconciliation procedure* that no
longer has any code following it — see the Truth Sync mandate below for the more precise current
state (the trigger files themselves are still written, just no longer read by anything). What's
below is the corrected, currently-accurate version; any agent working in this repo (Claude Code,
Gemini CLI, or otherwise) follows this.

## Layered architecture

- **Documentation layer** (`docs/`) — the source-of-truth rulebook and knowledge map. No code
  execution here.
- **Execution layer** (`execution/`) — deterministic Python scripts (`agent_actions.py`,
  `github_sync.py`, `repetition_processor.py`, etc.). Performs the actual work against the shared
  database. Must stay modular and testable.
- **Orchestration layer** (`orchestrator/`) — the LLM router. Interprets natural-language intent
  and calls the same Execution-layer functions a human or an AI coding agent would call directly.
  See `domains/system_architecture.md`.
- **Interface layer** (`dashboard_app/`) — the Flask web application for human oversight,
  rendering real-time state from the shared SQLite database.

## Mandatory before any non-trivial change

1. Read `docs/README.md` and the relevant `domains/` file(s) for the area being touched — don't
   assume the codebase still works the way an older doc (or memory) describes.
2. Use `docs/memory/documentation_policy.md` to know which doc(s) this change will need to update.

## Truth Sync mandate

All agent-driven mutations must be reflected in the shared database — never write to the SQLite
file directly. Two mechanisms exist:

- `execution/agent_actions.py` (entity creation/management) and `execution/log_progress.py`
  (status updates) both fire a `trigger_ui_refresh()` call, which POSTs to `/internal/notify-update`
  and fans out as an SSE event (`sse:datachanged`/`sse:toast`) so the browser dashboard updates
  itself with no polling and no manual reconciliation step.
- `execution/repetition_processor.py` is a third, narrower path that mutates `Task.status`
  directly via SQLAlchemy and reaches the same SSE outcome through a *different* pair of calls —
  `trigger_task_update()` (`dashboard_app/app/utils/trigger.py`) and `announcer.announce()`
  (`dashboard_app/app/utils/sse.py`) — not `trigger_ui_refresh()`. Any new automated-mutation
  script should go through `agent_actions.py`/`log_progress.py` unless it has as narrow and
  specific a purpose as this one.

**On the old file-based trigger mechanism** (`.tmp/triggers/`): this is *not* fully gone from the
code, despite an earlier pass through this doc claiming so. `dashboard_app/app/utils/trigger.py`'s
`trigger_task_update()`/`trigger_project_update()` still write a real `.trigger` file to disk on
every Task/Project update — called from `update_task_status()`/`update_project_status()`
(`dashboard_app/app/main/routes.py`) and from `repetition_processor.py` above. What's actually dead
is the *read side*: nothing anywhere in the codebase checks for, reconciles against, or deletes
these files anymore — the old SOP that once mandated checking them before acting is what no longer
applies, not the write itself. See `domains/flows.md` for the full corrected description.

## Self-annealing protocol

When a failure occurs or a gap in logic is found:

1. **Fix** — resolve the immediate issue in the code.
2. **Test** — verify the fix with a reproduction case.
3. **Update docs** — per `documentation_policy.md`, update whichever `domains/`/`architecture/`
   file described the now-outdated behavior, in the same change. A fix that leaves the docs
   describing the old, broken behavior isn't done yet.

## Post-task documentation duty

If you detect a discrepancy between the codebase and `docs/domains/`, treat updating the docs as
part of finishing the task, not a follow-up — see `documentation_policy.md`. Log any durable,
reusable lesson (not a one-off narrative) in `docs/memory/knowledge_base.md` or
`docs/memory/coding_standards.md`.
