# Issue Report: Plan PR linking counted PRs that only mentioned an issue

## Summary

The first sync of a real plan (64 issues across 5 repositories) attached PRs to issues they only
mentioned. A cross-referencing PR used to count as linked, which was the documented "accepted risk"
from report 21. With real data that marked 11 plan nodes as "PR needs attention" or "PR open" when
most of them had no PR. For example, one sub-teams PR whose description listed the issues it
unblocks was attached to six of them.

Now a cross-referencing PR counts only if it is about the issue:

- it closes the issue (`closingIssuesReferences`), or
- its head branch (`feat/421-…`, `issue-421`) carries the issue number, or
- its title (`… (#421)`) carries the issue number.

PRs that GitHub already lists as closing the issue count as before.

## Files Changed

- `execution/plan_sync.py`:
  - `PLAN_PR_FIELDS` now also reads `title`, `headRefName` and `closingIssuesReferences`.
  - New `pr_is_about`.
  - `_linked_prs` filters cross-references through `pr_is_about`.
  - The docstring states the new rule.
- `tests/test_plan_status.py`: 4 new tests (mention-only ignored, closing cross-reference counted,
  closing reference counted whatever its branch, `pr_is_about` matching without false hits on
  `#77`/`#170`). The Refs case now uses a branch. Total: 24.
- Docs: `domains/business_logic.md` (linked-PR rule), `memory/knowledge_base.md` (replaces the
  accepted-risk entry), `architecture/01-github-readonly-guardrail.md` (fields read),
  `domains/test_coverage.md`.

## Validation Performed

- `python -m unittest tests.test_plan_status` passes (24 tests). `test_plan_progress`,
  `test_plan_graph` and `test_plan_import` pass too.
- A dry run against the live GitHub data with read-only queries, nothing written:

  | Statuses | No PR | PR open | PR needs attention | Merged | Closed |
  |---|---|---|---|---|---|
  | Old rule | 42 | 8 | 11 | 2 | 1 |
  | New rule | 50 | 7 | 3 | 3 | 1 |

  Every change matches the plan document's own status table:
  - B-01 moves to its real PR, #446.
  - M-10 becomes merged through PR #231.
  - Seven issues that were only mentioned (B-04, B-05, B-16, B-17, B-18, B-22, B-27) drop to "no PR",
    and so does B-32.
  - B-15, B-11 and B-21 keep their own PRs with changes requested.

## Known Limitations

- A PR linked only by `Refs #N`, on a branch that does not carry the number and with no `(#N)` in
  its title, is now missed. The team's `<type>/<issue>-<desc>` branch convention avoids this.
  Otherwise use a closing keyword.
- One PR that implements several issues and closes none of them (e.g. `docs/221-…` covering #221
  and #228) is attached only to the issue its branch names.
