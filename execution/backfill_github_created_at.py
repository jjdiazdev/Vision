"""One-time backfill of Task.github_created_at from GitHub's issue.createdAt.

Why this exists: sync_once only re-fetches issues whose `updatedAt` moved since the last
poll, and sync_active_tasks_once only touches In-Progress/Testing Tasks. So rows that
predate the column are never visited and would stay NULL indefinitely -- sorting to the
bottom of their status bucket forever.

Why it is a script and not an Alembic data migration: docker/web/entrypoint.sh runs
`flask db upgrade` on EVERY web boot, so a migration needing a GitHub token and network
would make app startup depend on the GitHub API and could hard-fail the boot.

Why it is in execution/ and not dashboard_app/app/commands.py: dashboard_app/ contains no
GitHub API code at all -- execution/ owns every GitHub call and one-off script, per
docs/governance/03-agent-execution-protocol.md's layered architecture.

🔴 Read-only against GitHub: a `createdAt` query field, never a mutation. See
docs/architecture/01-github-readonly-guardrail.md.

Usage:
    python -m execution.backfill_github_created_at --dry-run
    python -m execution.backfill_github_created_at
    python -m execution.backfill_github_created_at --force --project-id 2
"""
import argparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from execution.agent_actions import parse_github_timestamp
from execution.db_client import get_session
from execution.github_sync import fetch_issues_by_number, get_rate_limit
# Lives in the worker, not github_sync -- it is the worker's polling-budget guard.
from execution.github_sync_worker import RATE_LIMIT_SAFETY_THRESHOLD
from dashboard_app.app.models import Project, Task

# Minimal selection on purpose: `number createdAt` are scalars, so each aliased issue() is
# ONE node and a 50-alias request costs 1 rate-limit point. Reusing ISSUE_FIELDS would pull
# three first:5 connections per alias (~15 nodes each) and cost roughly 8x for data we
# immediately discard.
CREATED_AT_FIELDS = "number createdAt"
DEFAULT_BATCH_SIZE = 50


def backfill(dry_run=False, force=False, batch_size=DEFAULT_BATCH_SIZE, project_id=None):
    session = get_session()
    totals = {"updated": 0, "already_set": 0, "missing_on_github": 0,
              "unparseable": 0, "requests": 0}
    errors = []

    remaining = get_rate_limit().get("remaining")
    print(f"[rate limit] {remaining} points remaining")
    if remaining is not None and remaining < RATE_LIMIT_SAFETY_THRESHOLD:
        print(f"ABORT: below the {RATE_LIMIT_SAFETY_THRESHOLD}-point safety threshold.")
        return 1

    # NOTE: deliberately NO `Project.status != BLOCKED` filter, unlike both sync passes.
    # They skip Blocked projects to avoid writing a stale *status* into rows the UI hides.
    # This writes only an immutable creation timestamp and never touches status, so that
    # reason does not apply -- and leaving those rows NULL would silently break ordering the
    # day someone un-blocks the project (which happened to a real project on 2026-09-03).
    projects = session.query(Project).filter(Project.github_repo.isnot(None))
    if project_id:
        projects = projects.filter(Project.id == project_id)

    for project in projects.all():
        owner, _, repo = project.github_repo.partition("/")
        q = session.query(Task).filter(Task.project_id == project.id,
                                       Task.github_issue_number.isnot(None))
        if not force:
            q = q.filter(Task.github_created_at.is_(None))
        tasks = q.all()
        if not tasks:
            continue
        print(f"\n[{project.github_repo}] {len(tasks)} task(s) to resolve")

        for start in range(0, len(tasks), batch_size):
            chunk = tasks[start:start + batch_size]
            numbers = [t.github_issue_number for t in chunk]
            try:
                got = fetch_issues_by_number(owner, repo, numbers,
                                             fields=CREATED_AT_FIELDS)
                totals["requests"] += 1
            except Exception as exc:
                print(f"  ERROR batch {start}: {exc}")
                errors.append((project.github_repo, start, str(exc)))
                continue

            for task in chunk:
                issue = got.get(task.github_issue_number)
                if issue is None:
                    # Deleted or transferred on GitHub -- stays NULL, counted not hidden.
                    totals["missing_on_github"] += 1
                    continue
                parsed = parse_github_timestamp(issue.get("createdAt"))
                if parsed is None:
                    totals["unparseable"] += 1
                    continue
                if task.github_created_at == parsed:
                    totals["already_set"] += 1
                    continue
                # 🔴 Direct session write -- NEVER agent_actions.update_task(). That would
                # fire trigger_ui_refresh() per row: 305 Notification rows in the history
                # panel, 305 SSE announcements and 305 toast sounds.
                if not dry_run:
                    task.github_created_at = parsed
                totals["updated"] += 1

            if not dry_run:
                session.commit()

    if dry_run:
        session.rollback()

    print("\n=== summary" + (" (DRY RUN, nothing written)" if dry_run else "") + " ===")
    for k, v in totals.items():
        print(f"  {k:<18} {v}")
    if errors:
        print(f"  {'errors':<18} {len(errors)}")
        for repo, start, msg in errors:
            print(f"    {repo} @ {start}: {msg[:110]}")
    session.close()
    return 1 if errors else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="resolve and report, write nothing")
    ap.add_argument("--force", action="store_true",
                    help="also refetch tasks that already have a value")
    ap.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    ap.add_argument("--project-id", type=int, help="limit to one Project")
    args = ap.parse_args()
    sys.exit(backfill(dry_run=args.dry_run, force=args.force,
                      batch_size=args.batch_size, project_id=args.project_id))
