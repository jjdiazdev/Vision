# Issue Report: Cap the Notification History at the newest 500 entries

## Summary

The `Notification` table behind the Dashboard's "Notification History" panel grew without limit.
Every toast persists a row, and a real org sync (hundreds of Tasks plus the plan cadence) produces
many. The only cleanup was manual: dismissing one entry or "Clear all".

The table now keeps the newest 500 rows. Every insert, from any of the three writers, prunes
everything older in the same transaction.

- **Order** is by `id` (insertion order, primary-key index), not `created_at`, which can tie.
- **Display** is unchanged: the panel still renders the 200 most recent rows.

## Files Changed

- `dashboard_app/app/models.py`: `NOTIFICATION_HISTORY_LIMIT = 500` and
  `prune_notifications(session, keep=...)`. It finds the 500th newest id, deletes every lower id,
  works with any SQLAlchemy session and does not commit.
- `execution/agent_actions.py` and `execution/log_progress.py`: `trigger_ui_refresh` flushes the
  new row and prunes before its commit, inside the existing try/except.
- `dashboard_app/app/main/routes.py`: `record_notification` prunes after adding the row, riding the
  caller's commit. Its own try/except keeps a failure from breaking the user's change.
- `tests/test_notification_retention.py` (new, 5 tests).
- Docs: `domains/business_logic.md`, `domains/flows.md`, `domains/test_coverage.md`, `README.md`.

## Validation Performed

These ran on a host virtualenv with the pinned dependencies, each suite in its own process:

- `tests.test_notification_retention`: 5 OK. It covers:
  - the 0/499/500/501 boundaries;
  - that the newest ids are kept;
  - the cap holding after an insert through `record_notification`, `agent_actions.trigger_ui_refresh`
    and `log_progress.trigger_ui_refresh`.
- `test_plan_progress` (9), `test_plan_status` (24), `test_github_sync` (16), `test_task_ordering`
  (12) and `test_timezone` (18): OK.
- `test_errors`: 1 error, the pre-existing `NameError: Orchestrator` already documented in
  `domains/test_coverage.md`. It is unrelated to this change.
- **Not run:** the containers. They need a rebuild to pick the change up.

## Known Limitations

- On the first insert after deployment, any existing excess beyond 500 is deleted in one go.
- The Clear-all confirmation shows the rendered count (at most 200) while it deletes every row (at
  most 500). This predates this change.
- `trigger_ui_refresh` is still duplicated in `agent_actions.py` and `log_progress.py`.

## Follow-up Recommendations

- Make `log_progress.py` import `trigger_ui_refresh` from `agent_actions` instead of keeping a copy.
- Make the Clear-all confirmation show the real row count.
