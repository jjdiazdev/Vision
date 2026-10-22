import os
import sys
import argparse
from datetime import datetime, timezone

# Add the project root to sys.path to allow importing dashboard_app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from execution.db_client import get_session
from dashboard_app.app.models import Employee, System, Project, Task, StatusEnum, ReviewStateEnum, Notification, Plan, PlanItem, PlanEdge
import json
import requests
import threading

def trigger_ui_refresh(message="update", toast=None, employee_id=None, task_id=None, project_id=None):
    """Notify the Flask app that a change happened to trigger SSE updates.

    `toast` is an optional {"message": str, "type": "success"|"error"|"info"} dict,
    shown as the same corner toast a manual dashboard edit produces — since this
    call has no HTTP response of its own to attach an HX-Trigger header to, it is
    instead delivered as a separate named SSE event the page listens for.

    Whenever `toast` is given, it's also persisted as a Notification row (dashboard
    history panel) — `employee_id`/`task_id`/`project_id` are a snapshot captured at
    event time (not a live lookup), so the card still displays/links sensibly even if
    the Task is later deleted. Wrapped in its own try/except so a persistence failure
    can never break the actual SSE notify below.
    """
    if toast:
        try:
            s = get_session()
            s.add(Notification(message=toast["message"], type=toast.get("type", "info"),
                                employee_id=employee_id, task_id=task_id, project_id=project_id))
            s.commit()
            s.close()
        except Exception as e:
            print(f"Error recording notification: {e}")

    def _notify():
        urls = [
            "http://127.0.0.1:5000/internal/notify-update",
            "http://127.0.0.1:5001/internal/notify-update",
            "http://web:5000/internal/notify-update"
        ]
        payload = {"message": message}
        if toast:
            payload["toast"] = toast
        for url in urls:
            try:
                requests.post(url, json=payload, timeout=0.1)
            except:
                pass

    # Run in a separate thread so it doesn't block the caller
    threading.Thread(target=_notify, daemon=True).start()

def parse_github_timestamp(value):
    """GraphQL ISO-8601 'Z' string -> naive-UTC datetime, matching TimestampMixin's convention.

    Accepts a datetime too (normalized, not re-parsed). Returns None for None/''/unparseable
    input and never raises, so a malformed field can't kill a sync cycle.

    The explicit Z -> +00:00 rewrite is redundant on 3.11+ (fromisoformat handles Z since
    3.11, and the container is 3.11.16) but keeps this working for a dev running the tests on
    a 3.10 host.
    """
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _resolve_system_id(session, github_repo):
    """Find-or-create the System matching a Project's github_repo org (e.g. "acme-org/foo" -> "acme-org")."""
    if not github_repo or "/" not in github_repo:
        return None
    org = github_repo.split("/")[0]
    system = session.query(System).filter_by(github_org=org).first()
    if system:
        return system.id
    system = System(name=org, github_org=org)
    session.add(system)
    session.commit()
    return system.id

# --- System Operations ---

def create_system(name, github_org=None):
    session = get_session()
    try:
        system = System(name=name, github_org=github_org)
        session.add(system)
        session.commit()
        msg = f"System '{system.name}' created successfully with ID: {system.id}"
        print(msg)
        trigger_ui_refresh("create_system", toast={"message": f"System '{system.name}' created successfully", "type": "success"})
        return msg
    except Exception as e:
        session.rollback()
        return f"Error creating system: {e}"
    finally:
        session.close()

def update_system(system_id, name=None, github_org=None):
    session = get_session()
    try:
        system = session.query(System).get(system_id)
        if not system:
            return f"System ID {system_id} not found."

        changed = False
        if name and system.name != name:
            system.name = name
            changed = True
        if github_org and system.github_org != github_org:
            system.github_org = github_org
            changed = True

        session.commit()
        msg = f"System '{system.name}' (ID: {system_id}) updated successfully."
        print(msg)
        if changed:
            trigger_ui_refresh("update_system", toast={"message": f"System '{system.name}' updated successfully", "type": "success"})
        return msg
    except Exception as e:
        session.rollback()
        return f"Error updating system: {e}"
    finally:
        session.close()

def delete_system(system_id):
    session = get_session()
    try:
        system = session.query(System).get(system_id)
        if not system:
            return f"System ID {system_id} not found."

        name = system.name
        session.delete(system)
        session.commit()
        msg = f"System '{name}' (ID: {system_id}) has been deleted."
        print(msg)
        trigger_ui_refresh("delete_system", toast={"message": f"System '{name}' deleted", "type": "success"})
        return msg
    except Exception as e:
        session.rollback()
        return f"Error deleting system: {e}"
    finally:
        session.close()

def list_systems():
    session = get_session()
    try:
        systems = session.query(System).all()
        if not systems:
            return "No systems found in the system."

        results = []
        for s in systems:
            results.append(f"ID: {s.id} | Name: {s.name} | GitHub Org: {s.github_org or 'None'}")

        msg = "Current Systems:\n" + "\n".join(results)
        print(msg)
        return msg
    except Exception as e:
        return f"Error listing systems: {e}"
    finally:
        session.close()

# --- Project Operations ---

def create_project(name, status="Todo", github_repo=None, system_id=None):
    session = get_session()
    try:
        if system_id is None and github_repo:
            system_id = _resolve_system_id(session, github_repo)
        project = Project(name=name, status=StatusEnum(status), github_repo=github_repo, system_id=system_id)
        session.add(project)
        session.commit()
        msg = f"Project '{project.name}' created successfully with ID: {project.id}"
        print(msg)
        trigger_ui_refresh("create_project", toast={"message": f"Project '{project.name}' created successfully", "type": "success"})
        return msg
    except Exception as e:
        session.rollback()
        return f"Error creating project: {e}"
    finally:
        session.close()

def update_project(project_id, name=None, status=None, github_repo=None, system_id=None):
    session = get_session()
    try:
        project = session.query(Project).get(project_id)
        if not project:
            return f"Project ID {project_id} not found."

        changed = False
        if name and project.name != name:
            project.name = name
            changed = True
        if status:
            new_status = StatusEnum(status)
            if project.status != new_status:
                project.status = new_status
                changed = True
        if github_repo:
            if project.github_repo != github_repo:
                project.github_repo = github_repo
                changed = True
            if system_id is None:
                system_id = _resolve_system_id(session, github_repo)
        if system_id is not None and project.system_id != system_id:
            project.system_id = system_id
            changed = True

        session.commit()
        msg = f"Project '{project.name}' (ID: {project_id}) updated successfully."
        print(msg)
        if changed:
            trigger_ui_refresh("update_project", toast={"message": f"Project '{project.name}' updated successfully", "type": "success"})
        return msg
    except Exception as e:
        session.rollback()
        return f"Error updating project: {e}"
    finally:
        session.close()

def delete_project(project_id):
    session = get_session()
    try:
        project = session.query(Project).get(project_id)
        if not project:
            return f"Project ID {project_id} not found."

        name = project.name
        session.delete(project)
        session.commit()
        msg = f"Project '{name}' (ID: {project_id}) has been deleted."
        print(msg)
        trigger_ui_refresh("delete_project", toast={"message": f"Project '{name}' deleted", "type": "success"})
        return msg
    except Exception as e:
        session.rollback()
        return f"Error deleting project: {e}"
    finally:
        session.close()

def list_projects(system_id=None):
    session = get_session()
    try:
        query = session.query(Project)
        if system_id:
            query = query.filter(Project.system_id == system_id)
        projects = query.all()
        if not projects:
            return "No projects found in the system."

        results = []
        for p in projects:
            results.append(f"ID: {p.id} | Name: {p.name} | Status: {p.status.value} | System ID: {p.system_id}")

        msg = "Current Projects:\n" + "\n".join(results)
        print(msg)
        return msg
    except Exception as e:
        return f"Error listing projects: {e}"
    finally:
        session.close()

# --- Task Operations ---

def create_task(name, project_id, employee_id=None, status="Todo", github_issue_number=None, github_pr_number=None, github_created_at=None):
    session = get_session()
    try:
        task = Task(
            name=name,
            project_id=project_id,
            employee_id=employee_id if employee_id and employee_id > 0 else None,
            status=StatusEnum(status),
            github_issue_number=github_issue_number,
            github_pr_number=github_pr_number,
            github_created_at=parse_github_timestamp(github_created_at)
        )
        session.add(task)
        session.commit()
        msg = f"Task '{task.name}' created successfully with ID: {task.id} in Project ID: {project_id}"
        print(msg)
        trigger_ui_refresh("create_task", toast={"message": f"Task '{task.name}' created", "type": "success"}, employee_id=task.employee_id, task_id=task.id, project_id=task.project_id)
        return msg
    except Exception as e:
        session.rollback()
        return f"Error creating task: {e}"
    finally:
        session.close()

def update_task(task_id, status=None, name=None, employee_id=None, project_id=None, github_issue_number=None, github_pr_number=None, github_review_state=None, github_created_at=None):
    session = get_session()
    try:
        task = session.query(Task).get(task_id)
        if not task:
            return f"Task ID {task_id} not found."

        changed = False
        if status:
            new_status = StatusEnum(status)
            if task.status != new_status:
                task.status = new_status
                changed = True
        if name and task.name != name:
            task.name = name
            changed = True
        if employee_id is not None:
            new_employee_id = employee_id if employee_id > 0 else None
            if task.employee_id != new_employee_id:
                task.employee_id = new_employee_id
                changed = True
        if project_id and task.project_id != project_id:
            task.project_id = project_id
            changed = True
        if github_issue_number is not None and task.github_issue_number != github_issue_number:
            task.github_issue_number = github_issue_number
            changed = True
        if github_pr_number is not None and task.github_pr_number != github_pr_number:
            task.github_pr_number = github_pr_number
            changed = True
        if github_review_state is not None:
            new_review_state = ReviewStateEnum(github_review_state) if github_review_state else None
            if task.github_review_state != new_review_state:
                task.github_review_state = new_review_state
                changed = True
        if github_created_at is not None:
            new_github_created = parse_github_timestamp(github_created_at)
            if new_github_created is not None and task.github_created_at != new_github_created:
                task.github_created_at = new_github_created
                # Deliberately does NOT set changed = True. This is machine-synced metadata
                # with no user action behind it, so the self-heal write must not toast
                # "Task 'X' updated" once per row the sync happens to touch -- and the 5s
                # cadence would make that a toast (with sound) every five seconds. The
                # commit below is unconditional, so the value still persists. This is a
                # documented exception to flows.md's no-op suppression rule, not a
                # violation: that rule exists to suppress meaningless toasts.

        session.commit()
        msg = f"Task '{task.name}' (ID: {task_id}) updated successfully."
        print(msg)
        if changed:
            trigger_ui_refresh("update_task", toast={"message": f"Task '{task.name}' updated", "type": "success"}, employee_id=task.employee_id, task_id=task.id, project_id=task.project_id)
        return msg
    except Exception as e:
        session.rollback()
        return f"Error updating task: {e}"
    finally:
        session.close()

def delete_task(task_id):
    session = get_session()
    try:
        task = session.query(Task).get(task_id)
        if not task:
            return f"Task ID {task_id} not found."

        name = task.name
        employee_id = task.employee_id
        project_id = task.project_id
        session.delete(task)
        session.commit()
        msg = f"Task '{name}' (ID: {task_id}) has been deleted."
        print(msg)
        trigger_ui_refresh("delete_task", toast={"message": f"Task '{name}' deleted", "type": "success"}, employee_id=employee_id, task_id=task_id, project_id=project_id)
        return msg
    except Exception as e:
        session.rollback()
        return f"Error deleting task: {e}"
    finally:
        session.close()

def list_tasks(project_id=None):
    session = get_session()
    try:
        query = session.query(Task)
        if project_id:
            query = query.filter(Task.project_id == project_id)

        tasks = query.all()
        if not tasks:
            return "No tasks found."

        results = []
        for t in tasks:
            assignee = t.assignee.name if t.assignee else "Unassigned"
            results.append(f"ID: {t.id} | Name: {t.name} | Status: {t.status.value} | Assignee: {assignee} | Project ID: {t.project_id}")

        msg = "Current Tasks:\n" + "\n".join(results)
        print(msg)
        return msg
    except Exception as e:
        return f"Error listing tasks: {e}"
    finally:
        session.close()

# --- Employee Operations ---

def create_employee(name):
    session = get_session()
    try:
        employee = Employee(name=name)
        session.add(employee)
        session.commit()
        msg = f"Employee '{employee.name}' added successfully with ID: {employee.id}"
        print(msg)
        trigger_ui_refresh("create_employee", toast={"message": f"Team member '{employee.name}' added successfully", "type": "success"})
        return msg
    except Exception as e:
        session.rollback()
        return f"Error adding employee: {e}"
    finally:
        session.close()

def update_employee(employee_id, name=None):
    session = get_session()
    try:
        employee = session.query(Employee).get(employee_id)
        if not employee:
            return f"Employee ID {employee_id} not found."

        changed = False
        if name and employee.name != name:
            employee.name = name
            changed = True

        session.commit()
        msg = f"Employee '{employee.name}' (ID: {employee_id}) updated successfully."
        print(msg)
        if changed:
            trigger_ui_refresh("update_employee", toast={"message": f"Team member '{employee.name}' updated successfully", "type": "success"})
        return msg
    except Exception as e:
        session.rollback()
        return f"Error updating employee: {e}"
    finally:
        session.close()

def delete_employee(employee_id):
    session = get_session()
    try:
        employee = session.query(Employee).get(employee_id)
        if not employee:
            return f"Employee ID {employee_id} not found."

        name = employee.name
        session.delete(employee)
        session.commit()
        msg = f"Employee '{name}' (ID: {employee_id}) has been deleted."
        print(msg)
        trigger_ui_refresh("delete_employee", toast={"message": f"Team member '{name}' deleted", "type": "success"})
        return msg
    except Exception as e:
        session.rollback()
        return f"Error deleting employee: {e}"
    finally:
        session.close()

def list_employees():
    session = get_session()
    try:
        employees = session.query(Employee).all()
        if not employees:
            return "No employees found."

        results = []
        for e in employees:
            results.append(f"ID: {e.id} | Name: {e.name}")

        msg = "Current Employees:\n" + "\n".join(results)
        print(msg)
        return msg
    except Exception as e:
        return f"Error listing employees: {e}"
    finally:
        session.close()


# --- Plan Operations ---

def _plan_project_map(session, repos):
    """{repo_lower: Project} for the repos a plan names; repos with no linked Project are absent."""
    wanted = {r.lower() for r in repos}
    projects = session.query(Project).filter(Project.github_repo.isnot(None)).all()
    return {p.github_repo.lower(): p for p in projects if p.github_repo.lower() in wanted}


def link_plan_item_tasks(session, items):
    """Point each issue PlanItem at the Task mirroring the same repo#issue, when one exists.
    Returns how many links changed. Does not commit."""
    projects = _plan_project_map(session, {i.repo for i in items if i.repo})
    changed = 0
    for item in items:
        if item.node_kind != "issue":
            continue
        project = projects.get(item.repo.lower())
        task = None
        if project:
            task = (session.query(Task)
                    .filter(Task.project_id == project.id, Task.github_issue_number == item.issue_number)
                    .first())
        task_id = task.id if task else None
        if item.task_id != task_id:
            item.task_id = task_id
            changed += 1
    return changed


def import_plan(path, activate=True, create_missing_projects=False):
    """Import a validated plan spec (JSON file, see execution/plan_import.py) for one System.

    Every repo the plan names must already be a Project with that github_repo, unless
    create_missing_projects is set -- github_sync never creates Projects, and neither does an
    import implicitly. One bulk write and a single UI refresh, not one per item."""
    from execution.plan_import import PlanSpecError, validate_plan_spec

    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError) as e:
        return f"Error importing plan: cannot read {path}: {e}"
    try:
        spec = validate_plan_spec(raw)
    except PlanSpecError as e:
        return f"Error importing plan: {e}"

    repos = sorted({n["repo"] for n in spec["nodes"]}, key=str.lower)
    session = get_session()
    try:
        projects = _plan_project_map(session, repos)
        missing = [r for r in repos if r.lower() not in projects]
        if missing and not create_missing_projects:
            return ("Error importing plan: no Project is linked to "
                    + ", ".join(missing)
                    + ". Link them with `project --create NAME --github-repo OWNER/REPO`, "
                      "or re-run with --create-missing-projects.")
        # All repos share the plan's org (validated), so they share one System. Resolved before
        # any other write: _resolve_system_id commits on its own when it creates the System.
        system_id = _resolve_system_id(session, repos[0])
        for repo in missing:
            session.add(Project(name=repo.split("/", 1)[1], status=StatusEnum.TODO, github_repo=repo,
                                system_id=system_id))
        session.flush()

        plan = Plan(name=spec["name"], system_id=system_id, target_date=spec["target_date"],
                    is_active=False, source_name=spec["source"] or os.path.basename(path),
                    spec_json=json.dumps(raw, ensure_ascii=False))
        session.add(plan)
        session.flush()

        groups = {g["key"]: g for g in spec["groups"]}
        items = []
        for position, node in enumerate(spec["nodes"]):
            item = PlanItem(plan_id=plan.id, position=position, key=node["key"],
                            display_key=node["display_key"], label=node["label"],
                            group_key=node["group"], group_label=groups[node["group"]]["label"],
                            repo=node["repo"], issue_number=node["issue"], node_kind=node["kind"])
            session.add(item)
            items.append(item)
        for position, edge in enumerate(spec["edges"]):
            session.add(PlanEdge(plan_id=plan.id, position=position, from_key=edge["from"],
                                 to_key=edge["to"], kind=edge["kind"], label=edge["label"]))
        link_plan_item_tasks(session, items)

        if activate:
            session.query(Plan).filter(Plan.system_id == system_id, Plan.id != plan.id).update({"is_active": False})
            plan.is_active = True
        session.commit()

        issue_count = sum(1 for i in items if i.node_kind == "issue")
        linked = sum(1 for i in items if i.task_id)
        msg = (f"Plan '{plan.name}' imported with ID: {plan.id} ({issue_count} issues, "
               f"{len(spec['edges'])} edges, {linked} linked to existing Tasks"
               + (f", {len(missing)} Projects created" if missing else "")
               + (", active)" if activate else ", inactive)"))
        print(msg)
        trigger_ui_refresh("import_plan", toast={"message": f"Plan '{plan.name}' imported", "type": "success"})
        return msg
    except Exception as e:
        session.rollback()
        return f"Error importing plan: {e}"
    finally:
        session.close()


def activate_plan(plan_id):
    """Make this the System's active plan (deactivating its other plans)."""
    session = get_session()
    try:
        plan = session.query(Plan).get(plan_id)
        if not plan:
            return f"Plan ID {plan_id} not found."
        if plan.is_active:
            return f"Plan '{plan.name}' (ID: {plan_id}) is already active."
        session.query(Plan).filter(Plan.system_id == plan.system_id, Plan.id != plan.id).update({"is_active": False})
        plan.is_active = True
        session.commit()
        msg = f"Plan '{plan.name}' (ID: {plan_id}) is now active."
        print(msg)
        trigger_ui_refresh("activate_plan", toast={"message": f"Plan '{plan.name}' is now active", "type": "success"})
        return msg
    except Exception as e:
        session.rollback()
        return f"Error activating plan: {e}"
    finally:
        session.close()


def deactivate_plan(plan_id):
    """Stop scoping progress to this plan; the dashboard falls back to all Tasks."""
    session = get_session()
    try:
        plan = session.query(Plan).get(plan_id)
        if not plan:
            return f"Plan ID {plan_id} not found."
        if not plan.is_active:
            return f"Plan '{plan.name}' (ID: {plan_id}) is already inactive."
        plan.is_active = False
        session.commit()
        msg = f"Plan '{plan.name}' (ID: {plan_id}) deactivated."
        print(msg)
        trigger_ui_refresh("deactivate_plan", toast={"message": f"Plan '{plan.name}' deactivated", "type": "success"})
        return msg
    except Exception as e:
        session.rollback()
        return f"Error deactivating plan: {e}"
    finally:
        session.close()


def delete_plan(plan_id):
    session = get_session()
    try:
        plan = session.query(Plan).get(plan_id)
        if not plan:
            return f"Plan ID {plan_id} not found."
        name = plan.name
        session.delete(plan)
        session.commit()
        msg = f"Plan '{name}' (ID: {plan_id}) has been deleted."
        print(msg)
        trigger_ui_refresh("delete_plan", toast={"message": f"Plan '{name}' deleted", "type": "success"})
        return msg
    except Exception as e:
        session.rollback()
        return f"Error deleting plan: {e}"
    finally:
        session.close()


def list_plans(system_id=None):
    session = get_session()
    try:
        query = session.query(Plan)
        if system_id:
            query = query.filter(Plan.system_id == system_id)
        plans = query.order_by(Plan.id.desc()).all()
        if not plans:
            return "No plans found."
        results = []
        for p in plans:
            issues = [i for i in p.items if i.node_kind == "issue"]
            target = p.target_date.isoformat() if p.target_date else "-"
            results.append(f"ID: {p.id} | Name: {p.name} | System ID: {p.system_id} | "
                           f"Active: {'yes' if p.is_active else 'no'} | Issues: {len(issues)} | Target: {target}")
        msg = "Plans:\n" + "\n".join(results)
        print(msg)
        return msg
    except Exception as e:
        return f"Error listing plans: {e}"
    finally:
        session.close()

# --- Global / Utility Operations ---

def navigate_to(destination):
    """
    Returns a standardized navigation string for the Orchestrator to parse.
    Maps human terms to internal route names.
    """
    # Mapping human terms to internal route names
    mapping = {
        "home": "index",
        "dashboard": "index",
        "staff": "employees",
        "team": "employees",
        "employees": "employees",
        "projects": "projects",
        "work": "projects",
        "tasks": "tasks",
        "systems": "systems",
        "organizations": "systems",
        "orgs": "systems"
    }

    # Normalize input
    target = destination.lower().strip()
    route = mapping.get(target, target)

    return f"NAVIGATE:{route}"

def chat_response(message=None):
    """
    Returns a direct conversational message from the AI.
    """
    return message

def search_entities(entity_type, query, message=None):
    """
    Searches for entities and returns their details as a string (Case-Insensitive).
    """
    session = get_session()
    try:
        results = []
        # Case-insensitive partial match
        search_filter = f"%{query}%"

        if entity_type == "employee":
            items = session.query(Employee).filter(Employee.name.ilike(search_filter)).all()
            results = [f"ID: {i.id} | Name: {i.name}" for i in items]
        elif entity_type == "system":
            items = session.query(System).filter(System.name.ilike(search_filter)).all()
            results = [f"ID: {i.id} | Name: {i.name}" for i in items]
        elif entity_type == "project":
            items = session.query(Project).filter(Project.name.ilike(search_filter)).all()
            results = [f"ID: {i.id} | Name: {i.name} | Status: {i.status.value}" for i in items]
        elif entity_type == "task":
            items = session.query(Task).filter(Task.name.ilike(search_filter)).all()
            results = [f"ID: {i.id} | Name: {i.name} | Status: {i.status.value}" for i in items]

        if not results:
            return f"No {entity_type}s found matching '{query}'."

        msg = "Found the following results:\n" + "\n".join(results)
        print(msg)
        return msg
    except Exception as e:
        return f"Error during search: {e}"
    finally:
        session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent Action CLI for Company Command Dashboard")
    subparsers = parser.add_subparsers(dest="command")

    # System commands
    system_parser = subparsers.add_parser("system", help="System operations")
    system_parser.add_argument("--create", help="Create a system with given name")
    system_parser.add_argument("--update", type=int, help="System ID to update")
    system_parser.add_argument("--delete", type=int, help="System ID to delete")
    system_parser.add_argument("--name", help="New name for the system")
    system_parser.add_argument("--github-org", help="GitHub organization login for the system")
    system_parser.add_argument("--list", action="store_true", help="List all systems")

    # Project commands
    project_parser = subparsers.add_parser("project", help="Project operations")
    project_parser.add_argument("--create", help="Create a project with given name")
    project_parser.add_argument("--update", type=int, help="Project ID to update")
    project_parser.add_argument("--delete", type=int, help="Project ID to delete")
    project_parser.add_argument("--name", help="New name for the project")
    project_parser.add_argument("--status", default="Todo", choices=["Todo", "In-Progress", "Testing", "Done", "Blocked"])
    project_parser.add_argument("--github-repo", help="Linked GitHub repo, e.g. 'acme-org/firmware'")
    project_parser.add_argument("--system-id", type=int, help="System ID this project belongs to (auto-derived from --github-repo if omitted)")
    project_parser.add_argument("--list", action="store_true", help="List all projects")

    # Task commands
    task_parser = subparsers.add_parser("task", help="Task operations")
    task_parser.add_argument("--create", help="Create a task with given name")
    task_parser.add_argument("--update", type=int, help="Task ID to update")
    task_parser.add_argument("--delete", type=int, help="Task ID to delete")
    task_parser.add_argument("--list", action="store_true", help="List all tasks")
    task_parser.add_argument("--name", help="New name for the task")
    task_parser.add_argument("--project-id", type=int, help="Project ID for the task (used for creation, and to filter tasks by --list)")
    task_parser.add_argument("--status", choices=["Todo", "In-Progress", "Testing", "Done", "Blocked", "Repeat Daily", "Repeat Weekly", "Repeat Monthly"])
    task_parser.add_argument("--employee-id", type=int, help="Employee ID for the task")
    task_parser.add_argument("--github-issue-number", type=int, help="Linked GitHub issue number for the task")
    task_parser.add_argument("--github-pr-number", type=int, help="Linked GitHub PR number for the task")

    # Employee commands
    employee_parser = subparsers.add_parser("employee", help="Employee operations")
    employee_parser.add_argument("--create", help="Create an employee with given name")
    employee_parser.add_argument("--update", type=int, help="Employee ID to update")
    employee_parser.add_argument("--delete", type=int, help="Employee ID to delete")
    employee_parser.add_argument("--list", action="store_true", help="List all employees")
    employee_parser.add_argument("--name", help="New name for the employee")

    # Plan commands
    plan_parser = subparsers.add_parser("plan", help="Implementation plan operations")
    plan_parser.add_argument("--import", dest="import_path", help="Import a plan spec JSON file (see docs/skills/import-plan/SKILL.md)")
    plan_parser.add_argument("--inactive", action="store_true", help="With --import: do not activate the imported plan")
    plan_parser.add_argument("--create-missing-projects", action="store_true", help="With --import: create a Project for each plan repo that has none")
    plan_parser.add_argument("--activate", type=int, help="Plan ID to make the active plan of its System")
    plan_parser.add_argument("--deactivate", type=int, help="Plan ID to deactivate")
    plan_parser.add_argument("--delete", type=int, help="Plan ID to delete")
    plan_parser.add_argument("--list", action="store_true", help="List all plans")
    plan_parser.add_argument("--system-id", type=int, help="With --list: only this System's plans")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search operations")
    search_parser.add_argument("--entity-type", required=True, choices=["employee", "system", "project", "task"], help="Type of entity to search for")
    search_parser.add_argument("--query", required=True, help="Name or partial name to search for")

    # Navigation command
    navigate_parser = subparsers.add_parser("navigate", help="Navigation operations")
    navigate_parser.add_argument("--to", required=True, help="Destination to navigate to")

    args = parser.parse_args()

    if args.command == "system":
        if args.create:
            print(create_system(args.create, github_org=args.github_org))
        elif args.update:
            print(update_system(args.update, name=args.name, github_org=args.github_org))
        elif args.delete:
            print(delete_system(args.delete))
        elif args.list:
            print(list_systems())

    elif args.command == "project":
        if args.create:
            print(create_project(args.create, args.status, github_repo=args.github_repo, system_id=args.system_id))
        elif args.update:
            print(update_project(args.update, name=args.name, status=args.status, github_repo=args.github_repo, system_id=args.system_id))
        elif args.delete:
            print(delete_project(args.delete))
        elif args.list:
            print(list_projects())

    elif args.command == "task":
        if args.create and args.project_id:
            print(create_task(args.create, args.project_id, args.employee_id, args.status or "Todo", args.github_issue_number, args.github_pr_number))
        elif args.update:
            print(update_task(args.update, status=args.status, name=args.name, employee_id=args.employee_id, project_id=args.project_id, github_issue_number=args.github_issue_number, github_pr_number=args.github_pr_number))
        elif args.delete:
            print(delete_task(args.delete))
        elif args.list:
            print(list_tasks(args.project_id))
        else:
            print("Error: Invalid task arguments.")

    elif args.command == "employee":
        if args.create:
            print(create_employee(args.create))
        elif args.update:
            print(update_employee(args.update, name=args.name))
        elif args.delete:
            print(delete_employee(args.delete))
        elif args.list:
            print(list_employees())


    elif args.command == "plan":
        if args.import_path:
            print(import_plan(args.import_path, activate=not args.inactive, create_missing_projects=args.create_missing_projects))
        elif args.activate:
            print(activate_plan(args.activate))
        elif args.deactivate:
            print(deactivate_plan(args.deactivate))
        elif args.delete:
            print(delete_plan(args.delete))
        elif args.list:
            print(list_plans(args.system_id))
        else:
            print("Error: Invalid plan arguments.")

    elif args.command == "search":
        print(search_entities(args.entity_type, args.query))

    elif args.command == "navigate":
        if args.to:
            print(navigate_to(args.to))
