# Documentation Policy — Which Doc to Update for Which Change

This is the file that keeps the rest of `docs/` from silently going stale. Update the relevant
doc(s) **in the same change**, not as a follow-up — an out-of-date `domains/` file is worse than
none, because it actively misleads the next reader (see this session's `max_iterations`
discrepancy in `memory/knowledge_base.md` — two different existing docs disagreed with the code,
and both were checked-in as if current).

| Kind of change | Update |
|---|---|
| New/changed Flask route | `domains/api_endpoints.md` |
| Schema change (new field, new model, new relationship) | `domains/business_logic.md`; if it's a durable, hard-to-reverse structural choice (not just adding a nullable column), also a new `adr/NNNN-*.md` |
| New/changed auto-status or business rule (e.g. in `github_sync.py`) | `domains/business_logic.md` |
| New/changed navigation destination or SSE/notification wiring | `domains/flows.md` |
| New/changed test file | `domains/test_coverage.md` |
| New `agent_actions.py` function or CLI subcommand | `governance/01-development-workflow.md` if it changes the data-vs-system-change dispatch rule; `orchestrator/manifest.py` and `orchestrator/prompts.py` stay in sync with it in the same change (see `system_architecture.md`) |
| New GitHub-facing code | Re-read `architecture/01-github-readonly-guardrail.md` first — it must stay inside that limit; the doc itself only needs an update if the limit's *mechanics* change (e.g. token scope), not for every new read-only query |
| A durable, hard-to-reverse technical decision | A new `adr/NNNN-*.md` — never edit an existing accepted ADR, a rethink supersedes it with a new one |
| A completed roadmap item | `01-roadmap.md`'s status table, plus a closing report in `reports/issues/` following `skills/write-closing-report/SKILL.md` |
| A new roadmap phase/item being planned | `01-roadmap.md`, optionally a spec in `reports/specs/` following the existing template if it's substantial enough to warrant a written work order first |
| A reusable coding convention discovered while fixing a bug | `memory/coding_standards.md` (the durable lesson) — the bug-fix narrative itself goes in `reports/`, dated, not rewritten later |
| Anything CLAUDE.md/GEMINI.md currently states as a fact (not a pointer) | Move the fact into the appropriate `docs/` file instead of editing it in place there — the entrypoint files must stay pointer-only, see `docs/README.md`'s governing principles |

## When in doubt

If a change doesn't obviously map to a row above, ask: is this describing **current codebase
state** (→ `domains/`), **a rule for how work happens** (→ `governance/`), **a durable, hard-to-
reverse decision** (→ `adr/`), or **evidence of what already happened** (→ `reports/`, never
edited after the fact)? Those four are mutually exclusive — if a change seems to need two of them,
it's actually two separate doc updates, not one hybrid one.
