"""Request-scoped view of the active implementation plans.

Everything here is computed at most once per request: the projects table, the system detail
page and the Tasks filter all ask the same questions while rendering one response.
"""

from flask import g, has_request_context, request

from dashboard_app.app.models import Plan, PlanItem, Project
from dashboard_app.app.utils.plan_graph import plan_progress


def _cache():
    """Per-request memo. Keyed by the request object, not just stored on g: an app context
    that outlives one request (tests push one for the whole suite, and Flask then reuses it
    for every request) would otherwise serve the first request's answer forever."""
    owner = request._get_current_object() if has_request_context() else None
    cached = g.get("_plan_cache")
    if cached is None or cached[0] is not owner:
        cached = (owner, {})
        g._plan_cache = cached
    return cached[1]


def active_plans():
    cache = _cache()
    if "active_plans" not in cache:
        cache["active_plans"] = Plan.query.filter_by(is_active=True).order_by(Plan.id).all()
    return cache["active_plans"]


def _scope():
    cache = _cache()
    if "plan_scope" not in cache:
        plans = active_plans()
        items = []
        if plans:
            items = (PlanItem.query
                     .filter(PlanItem.plan_id.in_([p.id for p in plans]), PlanItem.node_kind == "issue")
                     .all())
        projects = {}
        repos = {i.repo.lower() for i in items}
        if repos:
            for project in Project.query.filter(Project.github_repo.isnot(None)).all():
                if project.github_repo.lower() in repos:
                    projects[project.github_repo.lower()] = project.id
        statuses_by_project = {}
        for item in items:
            project_id = projects.get(item.repo.lower())
            if project_id is not None:
                status = item.plan_status.value if item.plan_status else None
                statuses_by_project.setdefault(project_id, []).append(status)
        cache["plan_scope"] = {
            "progress": {pid: plan_progress(s) for pid, s in statuses_by_project.items()},
            "task_ids": {i.task_id for i in items if i.task_id},
        }
    return cache["plan_scope"]


def plan_task_ids():
    """Task ids mirrored by an active plan's issues, or None when no plan is active."""
    return _scope()["task_ids"] if active_plans() else None


def project_progress(project):
    """Progress for the projects tables: scoped to the active plan's issues when the project's
    repo is in one, otherwise the legacy all-Tasks ratio (Project.progress)."""
    scoped = _scope()["progress"].get(project.id)
    if scoped:
        return {"percent": scoped["percent"], "complete": scoped["total"] > 0 and scoped["done"] == scoped["total"],
                "scoped": True, "done": scoped["done"], "total": scoped["total"]}
    return {"percent": project.progress, "complete": project.is_complete, "scoped": False,
            "done": None, "total": None}


def register_plan_context_processor(app):
    @app.context_processor
    def inject_plan_helpers():
        return dict(project_progress=project_progress)
