# SKILL: Write a Closing Report

## Goal

Every completed roadmap item gets a dated, append-only closing report in `docs/reports/issues/`,
so "what actually happened with item N" is answerable months later without digging through chat
history or git blame. This is the template all 21 existing reports already follow (with two
outliers using a slightly different header set — noted below).

## Inputs

- The roadmap item's `01-roadmap.md` entry (and its `reports/specs/` work-order, if one exists).
- The actual diff/files changed while implementing it.
- Whatever manual or automated verification was actually performed — never write "Validation
  Performed" content that wasn't actually run.

## Step-by-step logic

1. Pick the next sequence number. Check the highest-numbered file already in
   `docs/reports/issues/` — this project's numbering has two known irregularities (two files both
   numbered `12`, and no file numbered `17`); don't perpetuate a third one, but don't spend time
   fixing the old ones either (see `memory/documentation_policy.md`).
2. Filename: `docs/reports/issues/NN-kebab-case-slug.md`.
3. Use this structure (the standard template, followed by 19 of the 21 existing reports):
   ```markdown
   # Issue Report: <Title>

   ## Summary
   One paragraph: what was built/fixed and why.

   ## Files Changed
   - `path/to/file.py` — what changed there, one line

   ## Validation Performed
   What was actually run/checked to confirm it works — be specific (commands run, routes hit,
   test output), not just "tested and it works."

   ## Known Limitations
   Anything intentionally left incomplete or deferred.

   ## Follow-up Recommendations
   Concrete next steps, if any — not required if there genuinely are none.
   ```
4. The alternate header set (`Status` / `Problem Statement` / `Solution Implemented` /
   `Components Updated` / `Verification Results` / `Future Considerations`) is acceptable for a
   report that's more of a strategy/architecture writeup than a scoped feature closing — used once
   so far (`12-hybrid-intelligence-strategy.md`). Prefer the standard template unless the work
   genuinely doesn't fit it.
5. Never edit a closing report after the fact once it's committed — a correction gets a new, later
   report that references it, exactly like an ADR.

## Edge cases & failure modes

- **Work spans multiple roadmap items**: write one report per item if they're separable; one
  combined report only if the work was genuinely inseparable in practice.
- **The feature was later removed/replaced** (e.g. the Process/Milestone retirement in
  [ADR 0001](../../adr/0001-system-project-task-hierarchy.md)): the original closing report for
  that now-removed feature stays exactly as it was — it's still an accurate record of what
  happened at the time. The removal gets its own new report or ADR; it doesn't retroactively edit
  the old one.

## Change log

- 2026-08-27 — Skill authored, derived from the real pattern already established across the
  existing 21 `reports/issues/` files during the docs "second brain" migration.
