"""Read-only GitHub -> PlanItem live-state reconciliation (the plan graph's colors).

Separate from github_sync's Task reconciliation on purpose: a plan needs finer PR detail than a
Task status carries (draft, CI rollup, review decision, merged-but-issue-still-open), and its
issues can live in repos whose Project is Blocked or not yet synced. Task status rules are not
touched here -- see docs/memory/knowledge_base.md for why a Task can read Done while its plan
node reads "fusionada".

Plan status rule (the plan documents' status-color rule, computed by compute_plan_status):
- cerrada     issue closed as completed
- descartada  issue closed as not planned / duplicate (leaves the progress denominator)
- prbloq      selected PR open with CI FAILURE/ERROR, or reviewDecision CHANGES_REQUESTED
- conpr       selected PR open (drafts included)
- fusionada   selected PR merged, issue still open
- sinpr       anything else, including only closed-unmerged PRs

Selected PR: among PRs of the SAME repo linked by closing keyword/dev panel or by a
cross-reference (covers "Refs #N"), the open one wins, else the merged one; highest number
breaks ties. A cross-reference that merely mentions the issue also counts -- accepted risk.
A PR whose CI rollup can't be read (null) is never treated as failing.
"""

import logging
from datetime import datetime

from execution import agent_actions
from execution.github_sync import fetch_issues_by_number
from dashboard_app.app.models import Plan, PlanItem, PlanStatusEnum

logger = logging.getLogger("plan_sync")

PLAN_PR_FIELDS = """number state isDraft merged reviewDecision
            repository { nameWithOwner }
            commits(last: 1) { nodes { commit { statusCheckRollup { state } } } }"""

PLAN_ITEM_FIELDS = f"""
        number
        title
        state
        stateReason
        closedByPullRequestsReferences(first: 10, includeClosedPrs: true) {{ nodes {{ {PLAN_PR_FIELDS} }} }}
        timelineItems(last: 25, itemTypes: [CROSS_REFERENCED_EVENT]) {{
            nodes {{
                ... on CrossReferencedEvent {{
                    source {{ ... on PullRequest {{ {PLAN_PR_FIELDS} }} }}
                }}
            }}
        }}
"""

# Aliased issue(number:) fields per request; keeps one request's node count well under limits.
BATCH_SIZE = 25

FAILING_CI_STATES = ("FAILURE", "ERROR")
DISCARDED_STATE_REASONS = ("NOT_PLANNED", "DUPLICATE")

STATUS_PHRASES = {
    PlanStatusEnum.NO_PR: ("has no PR", "info"),
    PlanStatusEnum.PR_OPEN: ("PR #{pr} open", "info"),
    PlanStatusEnum.PR_BLOCKED: ("PR #{pr} needs attention", "error"),
    PlanStatusEnum.MERGED: ("PR #{pr} merged", "success"),
    PlanStatusEnum.CLOSED: ("issue closed", "success"),
    PlanStatusEnum.NOT_PLANNED: ("closed as not planned", "info"),
}

# Above this many transitions in one cycle, a single summary toast replaces per-item toasts.
MAX_TOASTS_PER_CYCLE = 3

SNAPSHOT_FIELDS = ("github_title", "issue_state", "issue_state_reason", "pr_number", "pr_state",
                   "pr_is_draft", "pr_ci_state", "pr_review_decision", "plan_status")


def _linked_prs(issue, repo):
    """Same-repo PRs linked to `issue`, deduped by number."""
    candidates = list(issue["closedByPullRequestsReferences"]["nodes"])
    for node in issue["timelineItems"]["nodes"]:
        source = (node or {}).get("source") or {}
        if "number" in source and "state" in source:
            candidates.append(source)
    prs = {}
    for pr in candidates:
        owner_repo = ((pr.get("repository") or {}).get("nameWithOwner") or "").lower()
        if owner_repo == repo.lower():
            prs[pr["number"]] = pr
    return list(prs.values())


def _ci_state(pr):
    nodes = ((pr.get("commits") or {}).get("nodes")) or []
    rollup = (nodes[-1].get("commit") or {}).get("statusCheckRollup") if nodes else None
    return rollup.get("state") if rollup else None


def select_pr(prs):
    open_prs = [p for p in prs if p["state"] == "OPEN"]
    if open_prs:
        return max(open_prs, key=lambda p: p["number"])
    merged = [p for p in prs if p["state"] == "MERGED" or p.get("merged")]
    if merged:
        return max(merged, key=lambda p: p["number"])
    return None


def compute_plan_snapshot(issue, repo):
    """Pure: GraphQL issue dict (PLAN_ITEM_FIELDS shape) -> PlanItem live-state field values."""
    pr = select_pr(_linked_prs(issue, repo))
    ci_state = _ci_state(pr) if pr else None
    review = pr.get("reviewDecision") if pr else None

    if issue["state"] == "CLOSED":
        if issue.get("stateReason") in DISCARDED_STATE_REASONS:
            status = PlanStatusEnum.NOT_PLANNED
        else:
            status = PlanStatusEnum.CLOSED
    elif pr and pr["state"] == "OPEN":
        if ci_state in FAILING_CI_STATES or review == "CHANGES_REQUESTED":
            status = PlanStatusEnum.PR_BLOCKED
        else:
            status = PlanStatusEnum.PR_OPEN
    elif pr:
        status = PlanStatusEnum.MERGED
    else:
        status = PlanStatusEnum.NO_PR

    return {
        "github_title": (issue.get("title") or "")[:300] or None,
        "issue_state": issue["state"],
        "issue_state_reason": issue.get("stateReason"),
        "pr_number": pr["number"] if pr else None,
        "pr_state": ("MERGED" if pr.get("merged") else pr["state"]) if pr else None,
        "pr_is_draft": bool(pr.get("isDraft")) if pr else None,
        "pr_ci_state": ci_state,
        "pr_review_decision": review,
        "plan_status": status,
    }


def compute_plan_status(issue, repo):
    return compute_plan_snapshot(issue, repo)["plan_status"]


def transition_toast(item):
    phrase, toast_type = STATUS_PHRASES[item.plan_status]
    who = item.display_key or item.key
    return {"message": f"{who} #{item.issue_number}: {phrase.format(pr=item.pr_number)}", "type": toast_type}


def _fetch_repo_items(repo, items):
    owner, _, name = repo.partition("/")
    results = {}
    numbers = [i.issue_number for i in items]
    for start in range(0, len(numbers), BATCH_SIZE):
        results.update(fetch_issues_by_number(owner, name, numbers[start:start + BATCH_SIZE], fields=PLAN_ITEM_FIELDS))
    return results


def sync_plan_once(session):
    """Refresh every issue PlanItem of every active Plan: one batched query per repo. Writes
    only rows whose snapshot changed, then refreshes the UI once per cycle (per-item toasts only
    for real status transitions, never for an item's first sync)."""
    summary = {"updated": 0, "transitions": 0, "errors": []}

    items = (
        session.query(PlanItem)
        .join(Plan)
        .filter(Plan.is_active.is_(True), PlanItem.node_kind == "issue")
        .all()
    )
    if not items:
        return summary

    by_repo = {}
    for item in items:
        by_repo.setdefault(item.repo, []).append(item)

    now = datetime.utcnow()
    transitions = []
    for repo, repo_items in by_repo.items():
        try:
            issues = _fetch_repo_items(repo, repo_items)
        except Exception as exc:
            logger.warning("Failed plan poll for %s: %s", repo, exc)
            summary["errors"].append((repo, str(exc)))
            continue

        for item in repo_items:
            issue = issues.get(item.issue_number)
            if not issue:
                continue  # deleted, transferred or inaccessible: keep the last known state
            snapshot = compute_plan_snapshot(issue, repo)
            changed = [f for f in SNAPSHOT_FIELDS if getattr(item, f) != snapshot[f]]
            item.last_synced_at = now
            if not changed:
                continue
            previous_status = item.plan_status
            for field in changed:
                setattr(item, field, snapshot[field])
            summary["updated"] += 1
            if "plan_status" in changed:
                item.status_changed_at = now
                if previous_status is not None:
                    transitions.append(item)

    if any(i.task_id is None for i in items):
        summary["updated"] += agent_actions.link_plan_item_tasks(session, items)
    session.commit()

    summary["transitions"] = len(transitions)
    if len(transitions) > MAX_TOASTS_PER_CYCLE:
        agent_actions.trigger_ui_refresh(
            "plan_sync", toast={"message": f"{len(transitions)} plan items changed status", "type": "info"})
    elif transitions:
        for item in transitions:
            task = item.task
            agent_actions.trigger_ui_refresh(
                "plan_sync", toast=transition_toast(item),
                employee_id=task.employee_id if task else None,
                task_id=task.id if task else None,
                project_id=task.project_id if task else None)
    elif summary["updated"]:
        agent_actions.trigger_ui_refresh("plan_sync")

    return summary
