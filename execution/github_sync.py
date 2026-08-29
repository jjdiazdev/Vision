"""Read-only GitHub -> local dashboard reconciliation.

Polls every non-Blocked Project that has a github_repo configured, and keeps its
Tasks in step with GitHub issue/PR state. Never writes anything back to GitHub.

Status auto-update rule:
- A still-open issue updates Todo/Testing/Done Tasks freely. An In-Progress Task only ever
  advances forward (to Testing once a PR is linked, to Done once it's closed/merged) and is
  never regressed back to Todo -- a human already claimed it. A Blocked Task is left alone.
- A closed issue is the highest-priority signal and overrides ANY current status, including
  Blocked: closed issue + a closed/merged PR -> Done; closed issue with no completed PR -> Blocked.
- Same top priority even while the issue is still open: if its only related PR(s) were closed
  without merging (abandoned), that's Blocked too -- GitHub drops a closed-unmerged PR from
  closedByPullRequestsReferences, so this is detected separately via timelineItems.
- Any Repeat_* status is always left untouched.

Review-state rule (5s active-task cadence only, see sync_active_tasks_once):
- For a Task's linked PR, if any reviewer's LATEST review (deduped per author, since GitHub
  never mutates an earlier review when a later one is submitted) is CHANGES_REQUESTED, the
  Task's github_review_state is set to CHANGES_REQUESTED -- unless a commit landed after that
  review's submittedAt, in which case it's CHANGES_APPLIED instead. With no outstanding
  CHANGES_REQUESTED review, it's cleared to None. This field is always cleared to None the
  moment a Task's computed status becomes Done or Blocked, since sync_active_tasks_once never
  revisits a Task once it leaves In-Progress/Testing. This is intentionally scoped to the fast
  cadence only -- a Todo Task with a PR under review is never colored.

Employee rule: always overwritten to mirror GitHub's current single-assignee
resolution (0 or 2+ assignees -> unassigned).

New-issue resolution: a Task attaches directly to the Project matching that repo --
no intermediate grouping.
"""

import html
import logging
import os
from datetime import datetime, timezone

import requests

from execution import agent_actions
from dashboard_app.app.models import Employee, Project, ReviewStateEnum, StatusEnum, Task

logger = logging.getLogger("github_sync")

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

PR_REF_FIELDS = "number state"

PR_REF_FIELDS_WITH_REVIEW = """number state
        reviews(last: 20, states: [APPROVED, CHANGES_REQUESTED]) {
            nodes { author { login } state submittedAt }
        }
        commits(last: 1) { nodes { commit { committedDate } } }
"""


def _issue_fields(pr_ref_fields):
    return f"""
        number
        title
        updatedAt
        closed
        assignees(first: 5) {{ nodes {{ login }} }}
        closedByPullRequestsReferences(first: 5) {{ nodes {{ {pr_ref_fields} }} }}
        timelineItems(first: 5, itemTypes: [CROSS_REFERENCED_EVENT]) {{
            nodes {{
                ... on CrossReferencedEvent {{
                    source {{
                        ... on PullRequest {{
                            number
                            state
                            merged
                        }}
                    }}
                }}
            }}
        }}
"""


# Used by the 60s discovery pass (fetch_repo_issues/ISSUES_QUERY) -- unchanged query shape.
ISSUE_FIELDS = _issue_fields(PR_REF_FIELDS)

# Used only by the 5s active-task pass (fetch_issues_by_number via sync_active_tasks_once), which
# additionally needs review/commit data to compute github_review_state. Kept out of ISSUE_FIELDS
# so the discovery pass's per-issue query cost never grows with this feature.
ISSUE_FIELDS_WITH_REVIEW = _issue_fields(PR_REF_FIELDS_WITH_REVIEW)

ISSUES_QUERY = f"""
query($owner: String!, $repo: String!, $after: String) {{
  repository(owner: $owner, name: $repo) {{
    issues(first: 10, after: $after, orderBy: {{field: UPDATED_AT, direction: DESC}}) {{
      nodes {{
{ISSUE_FIELDS}
      }}
      pageInfo {{ hasNextPage endCursor }}
    }}
  }}
}}
"""

RATE_LIMIT_QUERY = "query { rateLimit { remaining resetAt cost } }"

REPEAT_STATUSES = {StatusEnum.REPEAT_DAILY, StatusEnum.REPEAT_WEEKLY, StatusEnum.REPEAT_MONTHLY}


def _github_headers():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def get_rate_limit():
    resp = requests.post(GITHUB_GRAPHQL_URL, json={"query": RATE_LIMIT_QUERY}, headers=_github_headers(), timeout=10)
    resp.raise_for_status()
    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(f"GitHub GraphQL error checking rate limit: {payload['errors']}")
    return payload["data"]["rateLimit"]


def fetch_repo_issues(owner, repo, since=None):
    """Fetch issues ordered by UPDATED_AT DESC, stopping once an issue is not newer
    than `since` (a datetime). `since=None` does one full pass over all issues."""
    issues = []
    after = None
    while True:
        resp = requests.post(
            GITHUB_GRAPHQL_URL,
            json={"query": ISSUES_QUERY, "variables": {"owner": owner, "repo": repo, "after": after}},
            headers=_github_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(f"GitHub GraphQL error for {owner}/{repo}: {payload['errors']}")
        repo_data = payload["data"]["repository"]
        if repo_data is None:
            raise RuntimeError(f"Repository {owner}/{repo} not found or not accessible")

        connection = repo_data["issues"]
        stop = False
        for node in connection["nodes"]:
            if since is not None and node["updatedAt"] <= since:
                stop = True
                break
            issues.append(node)

        if stop or not connection["pageInfo"]["hasNextPage"]:
            break
        after = connection["pageInfo"]["endCursor"]

    return issues


def fetch_issues_by_number(owner, repo, numbers, fields=ISSUE_FIELDS):
    """Fetch a specific, small set of issues by number in ONE request, via GraphQL
    field aliasing. Returns {number: issue_dict_or_None}. `numbers` must all be ints
    (always true here: they come from our own github_issue_number column)."""
    if not numbers:
        return {}
    numbers = [int(n) for n in numbers]
    aliases = "\n".join(f"i{idx}: issue(number: {n}) {{ {fields} }}" for idx, n in enumerate(numbers))
    query = f'query {{ repository(owner: "{owner}", name: "{repo}") {{ {aliases} }} }}'

    resp = requests.post(GITHUB_GRAPHQL_URL, json={"query": query}, headers=_github_headers(), timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(f"GitHub GraphQL error for {owner}/{repo}: {payload['errors']}")
    repo_data = payload["data"]["repository"]
    if repo_data is None:
        raise RuntimeError(f"Repository {owner}/{repo} not found or not accessible")

    return {numbers[idx]: repo_data.get(f"i{idx}") for idx in range(len(numbers))}


def _abandoned_pr_refs(issue):
    """PRs that cross-referenced this issue and were closed WITHOUT merging. GitHub drops a
    closed-unmerged PR from closedByPullRequestsReferences, so this has to come from
    timelineItems instead -- the only place that still shows it once abandoned."""
    sources = (node.get("source") or {} for node in issue["timelineItems"]["nodes"])
    return [s for s in sources if s.get("state") == "CLOSED" and not s.get("merged")]


def _compute_status(issue):
    refs = issue["closedByPullRequestsReferences"]["nodes"]
    has_pr = bool(refs)
    pr_closed = any(r["state"] in ("MERGED", "CLOSED") for r in refs)

    if issue["closed"]:
        return StatusEnum.DONE if (has_pr and pr_closed) else StatusEnum.BLOCKED
    if has_pr:
        return StatusEnum.DONE if pr_closed else StatusEnum.TESTING
    if _abandoned_pr_refs(issue):
        return StatusEnum.BLOCKED
    return StatusEnum.TODO


def _should_auto_update(current_status, computed_status):
    """Whether a sync pass should write `computed_status` over a Task's current one.

    A closed issue is the highest-priority signal and always wins, even over a
    manually-set Blocked status. A still-open issue only ever advances a Task
    forward (never regresses In-Progress back to Todo) and never touches Blocked
    or any Repeat_* status."""
    if current_status == computed_status or current_status in REPEAT_STATUSES:
        return False
    if computed_status in (StatusEnum.DONE, StatusEnum.BLOCKED):
        return True
    if current_status in (StatusEnum.TODO, StatusEnum.TESTING, StatusEnum.DONE):
        return True
    if current_status == StatusEnum.IN_PROGRESS:
        return computed_status != StatusEnum.TODO
    return False


def _compute_pr_number(issue):
    refs = issue["closedByPullRequestsReferences"]["nodes"]
    if refs:
        merged = [r for r in refs if r["state"] == "MERGED"]
        return merged[0]["number"] if merged else refs[0]["number"]
    abandoned = _abandoned_pr_refs(issue)
    return abandoned[0]["number"] if abandoned else None


def _compute_review_state(issue, pr_number):
    """Derives github_review_state from a PR ref's `reviews`/`commits` sub-selections
    (only present when the issue was fetched via ISSUE_FIELDS_WITH_REVIEW). Reviews are
    deduped to each author's LATEST submission first -- GitHub never mutates an earlier
    review's state when the same author submits a later one, so without this an old
    CHANGES_REQUESTED review would stay "outstanding" even after that same reviewer
    approved. submittedAt/committedDate are ISO 8601 strings, safe to compare directly."""
    if not pr_number:
        return None
    refs = issue["closedByPullRequestsReferences"]["nodes"]
    ref = next((r for r in refs if r["number"] == pr_number), None)
    if not ref or "reviews" not in ref:
        return None

    latest_by_author = {}
    for review in ref["reviews"]["nodes"]:
        author = review.get("author")
        login = author["login"] if author else None
        if not login:
            continue
        if login not in latest_by_author or review["submittedAt"] > latest_by_author[login]["submittedAt"]:
            latest_by_author[login] = review

    outstanding = [r for r in latest_by_author.values() if r["state"] == "CHANGES_REQUESTED"]
    if not outstanding:
        return None

    latest_request_at = max(r["submittedAt"] for r in outstanding)
    commit_nodes = ref.get("commits", {}).get("nodes", [])
    latest_commit_at = commit_nodes[-1]["commit"]["committedDate"] if commit_nodes else None

    if latest_commit_at and latest_commit_at > latest_request_at:
        return ReviewStateEnum.CHANGES_APPLIED
    return ReviewStateEnum.CHANGES_REQUESTED


def _resolve_employee_id(session, assignee_logins):
    if len(assignee_logins) != 1:
        return None
    login = assignee_logins[0]
    employee = session.query(Employee).filter_by(name=login).first()
    if employee:
        return employee.id
    agent_actions.create_employee(login)
    # create_employee commits via its own separate session/connection; commit here
    # too so this session's next query opens a fresh transaction and actually sees it.
    session.commit()
    employee = session.query(Employee).filter_by(name=login).first()
    return employee.id if employee else None


def sync_once(session, last_polled):
    """Reconcile every non-Blocked, github_repo-configured Project's Tasks against
    GitHub. `last_polled` is a {project_id: iso_datetime_str} dict mutated in place
    across calls so each cycle only re-fetches issues changed since the last one.
    Returns a summary dict for logging."""
    summary = {"created": 0, "updated": 0, "errors": []}

    projects = (
        session.query(Project)
        .filter(Project.status != StatusEnum.BLOCKED, Project.github_repo.isnot(None))
        .all()
    )

    for project in projects:
        owner, _, repo = project.github_repo.partition("/")
        try:
            since = last_polled.get(project.id)
            issues = fetch_repo_issues(owner, repo, since=since)
        except Exception as exc:
            logger.warning("Failed to poll %s: %s", project.github_repo, exc)
            summary["errors"].append((project.github_repo, str(exc)))
            continue

        for issue in issues:
            number = issue["number"]
            assignee_logins = [a["login"] for a in issue["assignees"]["nodes"]]
            employee_id = _resolve_employee_id(session, assignee_logins)
            computed_status = _compute_status(issue)
            pr_number = _compute_pr_number(issue)

            existing_task = (
                session.query(Task)
                .filter(Task.project_id == project.id, Task.github_issue_number == number)
                .first()
            )

            if existing_task:
                update_kwargs = {"employee_id": employee_id if employee_id is not None else 0}
                if _should_auto_update(existing_task.status, computed_status):
                    update_kwargs["status"] = computed_status.value
                if pr_number:
                    update_kwargs["github_pr_number"] = pr_number
                agent_actions.update_task(existing_task.id, **update_kwargs)
                session.commit()
                summary["updated"] += 1
                logger.info(
                    "Updated Task %s (%s#%s): status=%s employee_id=%s",
                    existing_task.id, project.github_repo, number,
                    update_kwargs.get("status", existing_task.status.value), employee_id,
                )
            else:
                title = html.unescape(issue["title"])
                agent_actions.create_task(
                    title, project.id, employee_id, computed_status.value,
                    github_issue_number=number, github_pr_number=pr_number,
                )
                session.commit()
                summary["created"] += 1
                logger.info(
                    "Created Task for %s#%s under Project %s: status=%s employee_id=%s",
                    project.github_repo, number, project.id, computed_status.value, employee_id,
                )

        # ISO 8601 string, comparable lexicographically with GraphQL's updatedAt format
        last_polled[project.id] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return summary


def sync_active_tasks_once(session):
    """Fast, narrow pass: re-check only Tasks currently In-Progress/Testing, one
    batched request per repo that actually has any, skipping repos with none.

    In-Progress Tasks only ever advance forward here (to Testing once a PR is
    linked, to Done once it's closed/merged, or straight to Blocked if their issue
    closes without a completed PR) — never regressed back to Todo. Testing Tasks
    can transition to Done or Blocked the same way. See _should_auto_update. Never
    creates Tasks or discovers new issues — that stays exclusively in sync_once."""
    summary = {"updated": 0, "errors": []}

    projects = (
        session.query(Project)
        .filter(Project.status != StatusEnum.BLOCKED, Project.github_repo.isnot(None))
        .all()
    )

    for project in projects:
        active_tasks = (
            session.query(Task)
            .filter(
                Task.project_id == project.id,
                Task.status.in_([StatusEnum.IN_PROGRESS, StatusEnum.TESTING]),
                Task.github_issue_number.isnot(None),
            )
            .all()
        )
        if not active_tasks:
            continue

        owner, _, repo = project.github_repo.partition("/")
        numbers = [t.github_issue_number for t in active_tasks]
        try:
            issues_by_number = fetch_issues_by_number(owner, repo, numbers, fields=ISSUE_FIELDS_WITH_REVIEW)
        except Exception as exc:
            logger.warning("Failed active-task poll for %s: %s", project.github_repo, exc)
            summary["errors"].append((project.github_repo, str(exc)))
            continue

        for task in active_tasks:
            issue = issues_by_number.get(task.github_issue_number)
            if not issue:
                continue  # issue deleted/inaccessible; leave the Task as-is

            assignee_logins = [a["login"] for a in issue["assignees"]["nodes"]]
            employee_id = _resolve_employee_id(session, assignee_logins)
            computed_status = _compute_status(issue)
            pr_number = _compute_pr_number(issue)
            review_state = None if computed_status in (StatusEnum.DONE, StatusEnum.BLOCKED) else _compute_review_state(issue, pr_number)

            update_kwargs = {
                "employee_id": employee_id if employee_id is not None else 0,
                "github_review_state": review_state.value if review_state else "",
            }
            if _should_auto_update(task.status, computed_status):
                update_kwargs["status"] = computed_status.value
            if pr_number:
                update_kwargs["github_pr_number"] = pr_number

            agent_actions.update_task(task.id, **update_kwargs)
            session.commit()
            summary["updated"] += 1
            logger.info(
                "Active-task recheck: Task %s (%s#%s) status=%s employee_id=%s",
                task.id, project.github_repo, task.github_issue_number,
                update_kwargs.get("status", task.status.value), employee_id,
            )

    return summary
