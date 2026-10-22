# ADR 0003: Progress scoped to an imported implementation plan, with its own GitHub status rule

## Status

Accepted

## Date

2026-10-22

## Context

`Project.progress` was `Done / all Tasks` of the repo, and every open issue of a linked repo
became a Task. The team works in short cycles: plan → implement → test → next plan, each cycle a
subset of a few repos' issues with a dependency DAG (stacked PRs inside a repo, contract/staging
conditions across repos), written as a Markdown document ending in a Mermaid `graph LR`. Against
that way of working the dashboard's percentage was meaningless: old backlog issues sat in the
denominator, and nothing showed which issue blocks which.

The plan documents also define a finer status rule than a Task status: no PR / PR open / PR with
red CI or changes requested / PR merged but issue still open (staging check pending) / closed.
The sync read none of draft, CI, `reviewDecision` or `stateReason`, and `_compute_status` maps a
merged PR to `Done`.

Alternatives considered:
- **Parse the Mermaid block in Python.** Rejected: the documents mix languages ("fusionada",
  "contrato"), hold several graphs (packages vs. issues), name repos only in prose, and include
  nodes without `#N`. A parser would be either fragile or a second, worse LLM.
- **Use GitHub milestones/projects as the plan.** Rejected: needs writes to GitHub to set up
  (guardrail `architecture/01`), and carries no edge kinds.
- **Reuse Task status for the graph.** Rejected: Task status has no "merged, issue open" and no
  CI/review signal; changing `_compute_status` would change every Task and every toast.
- **Count only closed issues as done.** Raised and rejected by the PM on 2026-10-22: merged
  counts as done for the percentage; the graph still distinguishes the two.

## Decision

1. New tables `plan`, `plan_item`, `plan_edge` (migration `d5e6f7a8b9c0`). One active plan per
   System.
2. Plans enter only as a validated JSON spec: an agent converts the Markdown following
   `skills/import-plan/SKILL.md`, and `agent_actions plan --import` validates it
   (`execution/plan_import.py`: schema, acyclic, same-org repos, same-repo-only stack edges).
   Every repo must already be a Project unless `--create-missing-projects` is given by a human.
3. A third worker cadence (`plan_sync.sync_plan_once`, 15s) reads the plan issues' live state
   and computes `PlanStatusEnum` independently of Task status.
4. With an active plan, a Project's percentage is `(merged + closed) / (plan issues − not
   planned)` and the Tasks list defaults to the plan's issues; without one, nothing changes.
5. The Tasks view gets a List/Graph switch; the graph is rendered client-side by pinned Mermaid
   11.4.1 from source the server builds, keeping the plan documents' notation and colors.
6. Because new queries were added, the read-only guardrail is now enforced in code
   (`graphql_query` / `assert_read_only`).

## Consequences

- Easier: the weekly percentage means "how much of this plan is done"; the graph answers "what
  can start now" and shows stack/condition edges relaxing as parents merge.
- Two status vocabularies now coexist for the same issue (Task `Done` vs. plan `fusionada`).
  Intentional and documented in `memory/knowledge_base.md`, but it is a source of confusion.
- A cross-referenced PR that merely mentions `#N` counts as linked (accepted for `Refs #N`
  support). PRs from other repos are ignored.
- More GitHub budget: one query per plan repo every 15s with CI rollups. Still gated by the
  shared rate-limit pause.
- First dashboard page depending on a heavier CDN script (Mermaid). It is pinned, loaded only
  on the graph view, and the list view never needs it.
- Plans of different Systems can be active at once; the graph shows one at a time with a
  selector.
- Follow-ups not done here: importing from the HUD chat, editing a plan in the UI, plan history
  or burndown.

---

Never edit this file once it's accepted. A later rethink gets a **new** ADR that references and
supersedes this one — this file stays exactly as it was when the decision was made, as the
historical record of what was known and decided at the time.
