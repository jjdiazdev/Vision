# SKILL: Import an implementation plan

## Goal

Turn an implementation-plan document (Markdown with an issue list per repo and a Mermaid
`graph LR` of dependencies) into the plan spec JSON that
`python -m execution.agent_actions plan --import` accepts, so progress and the Tasks graph view
count only that plan's issues. This is a **data operation** (`governance/01`): no code changes.

## Inputs

- The plan document the user names. It is usually **not** versioned in this repo and must stay
  that way: plan documents carry real org/repo names, which versioned files must not contain.
  Write the JSON outside the repo too (a scratch directory, or `dashboard_app/instance/`, which is
  git-ignored for `*.db` only — prefer a scratch directory).
- The org's repos must already be Projects with `github_repo` set (`project --list`). If some are
  missing, ask the user whether to link them first or to import with
  `--create-missing-projects`.

## Tools to use

- `execution/plan_import.py` — the spec schema (module docstring) and validator.
- `execution/agent_actions.py plan --import|--list|--activate|--deactivate|--delete`.
- GitHub (MCP or web) **read-only**, only to confirm an issue number you cannot resolve from the
  document. Never write to GitHub (`architecture/01`).

## Step-by-step logic

1. **Pick the right graph.** A document can hold several Mermaid blocks: work packages, waves,
   progress snapshots. Use the **issue** graph: the one whose nodes carry `#N` issue numbers and
   whose subgraphs are repos. If both a dependency graph and a "progress snapshot" exist, use the
   dependency graph — the snapshot already relaxed stacks by hand, and the sync now does that live.
2. **Name the plan and org.** `name`: the document's title or phase ("Phase 2"). `org`: the GitHub
   organization from the document's repo list. `target_date`: the deadline if the document states
   one (YYYY-MM-DD), else omit it. `source`: the document's file name.
3. **One group per repo subgraph.** `key` = the subgraph id (`API`, `WEB`), `label` = its title,
   `repo` = `org/name`. Resolve the repo name from the document's repo list or headings when the
   subgraph title abbreviates it ("Backend · api").
4. **Nodes.**
   - Base branch nodes (`apimain(("origin/main"))`, `imbase((...))`) → `"kind": "base"`, `label`
     = the branch.
   - Issue nodes → `key` = the Mermaid node id, `issue` = the `#N` in its label, `display_key` =
     the plan key if the label has one (`B-11`), `label` = the short title from the label (drop the
     `#N`, PR numbers, `✅` marks and wave suffixes like `· O1`).
   - A node whose issue has no `#` ("Issue 35 · existing") still gets `issue: 35`.
   - A node that lives in another repo than its subgraph says gets an explicit `"repo"`.
   - Package nodes (`P2-10`) and context nodes for other repos are **not** issues: leave them out.
5. **Edges**, mapping the plan notation:
   | Mermaid | `kind` |
   |---|---|
   | `base --> X` | `base` |
   | `A == stacked ==> B`, `A ==> B` | `stacked` |
   | `A -.->\|fusionada\|/\|merged\| B` (same repo) | `after_merge`, keep the label |
   | `A -.->\|contract\|staging\|…\| B` (across repos) | `cross`, keep the label |
   | `A --> B` between two issues of one repo | `after_merge` with no label |
   Edges to or from nodes you left out are dropped.
6. **Validate and import** inside the web container (dependencies are not on the host):
   ```bash
   docker cp /path/to/plan.json vision-web-1:/tmp/plan.json
   docker exec vision-web-1 python -m execution.agent_actions plan --import /tmp/plan.json
   ```
   Every validation error comes back at once with its JSON path; fix the JSON, not the code.
   Importing activates the plan and deactivates the System's previous one (`--inactive` to skip).
7. **Check the result**: `plan --list`, then the Tasks → Graph view. Node colors appear after the
   first plan sync cycle (≤ `PLAN_SYNC_INTERVAL_SECONDS`, 15s by default).

## Edge cases & failure modes

- **Cycle reported**: the document's graph has an arrow drawn backwards (often a condition
  arrow). Re-read the document's prose about that dependency; do not drop edges silently — ask.
- **"crosses repositories" on a stacked edge**: the document stacks across repos, which a PR
  cannot do. Import it as `cross` and tell the user.
- **Duplicate issue**: the same `repo#N` drawn twice (e.g. in a snapshot and a graph). Keep one.
- **Repo not linked**: the import refuses and names the repos. Linking is a separate data op.
- **The plan changes mid-cycle**: re-import the new version (it becomes the active plan); delete
  the old one only if the user asks.

## Change log

- 2026-10-22 — created with the plan graph feature (ADR 0003).
