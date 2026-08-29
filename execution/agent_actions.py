import os
import sys
import argparse
from datetime import datetime

# Add the project root to sys.path to allow importing dashboard_app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from execution.db_client import get_session
from dashboard_app.app.models import Employee, System, Project, Task, StatusEnum, ReviewStateEnum, Notification
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

def create_task(name, project_id, employee_id=None, status="Todo", github_issue_number=None, github_pr_number=None):
    session = get_session()
    try:
        task = Task(
            name=name,
            project_id=project_id,
            employee_id=employee_id if employee_id and employee_id > 0 else None,
            status=StatusEnum(status),
            github_issue_number=github_issue_number,
            github_pr_number=github_pr_number
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

def update_task(task_id, status=None, name=None, employee_id=None, project_id=None, github_issue_number=None, github_pr_number=None, github_review_state=None):
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


    elif args.command == "search":
        print(search_entities(args.entity_type, args.query))

    elif args.command == "navigate":
        if args.to:
            print(navigate_to(args.to))
