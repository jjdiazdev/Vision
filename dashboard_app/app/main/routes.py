from flask import render_template, request, redirect, url_for, Response, stream_with_context, make_response, session, current_app, abort
from werkzeug.security import check_password_hash
from dashboard_app.app.main import bp
from dashboard_app.app.models import Task, Project, StatusEnum, Employee, System, ChatMessage, Notification
from dashboard_app.app.extensions import db
from dashboard_app.app.utils.trigger import trigger_task_update, trigger_project_update
from dashboard_app.app.utils.sse import announcer
from orchestrator.brain import Orchestrator
from datetime import datetime, timezone
import json

def record_notification(message, type='info', employee_id=None, task_id=None, project_id=None):
    """Persists a Notification row (dashboard history panel) for a toast shown via the
    HX-Trigger mechanism (as opposed to trigger_ui_refresh's SSE mechanism, which persists
    its own toasts internally — see execution/agent_actions.py). Does not commit; rides
    the caller's existing db.session.commit()."""
    db.session.add(Notification(message=message, type=type, employee_id=employee_id, task_id=task_id, project_id=project_id))

# Endpoints reachable without an authenticated session: the login form itself, and the
# internal server-to-server notify hook (trigger_ui_refresh() in agent_actions.py/github_sync.py
# calls this over loopback with no browser session cookie).
EXEMPT_ENDPOINTS = {'main.login', 'main.notify_update'}

@bp.before_request
def require_admin_auth():
    if session.get('authenticated') or request.endpoint in EXEMPT_ENDPOINTS:
        return
    if request.method != 'GET' or request.path.startswith('/api/') or request.endpoint in ('main.stream', 'main.agent_chat'):
        abort(401)
    return render_template('lock.html')

@bp.route('/login', methods=['POST'])
def login():
    password = request.form.get('password', '')
    stored_hash = current_app.config.get('ADMIN_PASSWORD')
    if stored_hash and check_password_hash(stored_hash, password):
        session['authenticated'] = True
        # Always the Dashboard tab after login, regardless of which page was originally requested.
        return redirect(url_for('main.index'))
    # 200, not 401: <body> has hx-boost="true" app-wide, and htmx only swaps the DOM on a
    # 2xx response by default — a 401 here would silently drop the re-rendered error message.
    return render_template('lock.html', error=True)

@bp.route('/stream')
def stream():
    def event_stream():
        messages = announcer.listen()  # Get a queue for this user
        while True:
            msg = messages.get()  # Block until an announcement is made
            yield msg

    return Response(stream_with_context(event_stream()), mimetype='text/event-stream')

# Internal endpoint to trigger updates from scripts
@bp.route('/internal/notify-update', methods=['POST'])
def notify_update():
    msg = request.json.get('message', 'update') if request.is_json else 'update'
    print(f"[SSE] Notification received: {msg}")
    announcer.announce(msg)

    toast = request.json.get('toast') if request.is_json else None
    if toast and toast.get('message'):
        announcer.announce(json.dumps(toast), event="toast")

    return {}, 204

@bp.route('/agent/chat', methods=['POST'])
def agent_chat():
    user_message = request.form.get('message')
    if not user_message:
        return ""

    # Persist User Message
    chat_msg = ChatMessage(role='user', content=user_message)
    db.session.add(chat_msg)
    db.session.commit()

    # Retrieve Recent History (last 10 messages)
    history_records = ChatMessage.query.order_by(ChatMessage.created_at.desc()).limit(11).all()
    history_records.reverse() # Order chronologically

    # Convert to format Orchestrator expects
    # Note: We exclude the very last one we just added because it's passed as user_input
    initial_history = []
    for h in history_records[:-1]:
        prefix = "User: " if h.role == 'user' else "Assistant: "
        initial_history.append(f"{prefix}{h.content}")

    # Get backend preference from header (default to local)
    backend = request.headers.get('X-LLM-Backend', 'local')
    is_voice = request.headers.get('X-Voice-Command') == 'true'

    print(f"[Routes] Chat request received. Backend: {backend}, Voice: {is_voice}")
    if is_voice:
        print("[Routes] Voice Command Detected - Follow-up window (4s) will be triggered after response.")

    # Call Orchestrator
    orchestrator = Orchestrator()
    response = orchestrator.process_command(user_message, backend=backend, initial_history=initial_history)

    # Check for errors to trigger HUD alert
    trigger_data = {}
    if response['status'] == 'success':
        ai_message = response.get('result', "Action executed successfully.")
    else:
        ai_message = f"Error: {response.get('message', 'Unknown error occurred.')}"
        trigger_data["vision-alert"] = {"message": response.get('message', 'AI Orchestrator Error'), "type": "error"}
        record_notification(response.get('message', 'AI Orchestrator Error'), type='error')

    # Persist AI Response
    ai_msg = ChatMessage(role='ai', content=ai_message)
    db.session.add(ai_msg)
    db.session.commit()

    # Create the response
    response_html = render_template('partials/_chat_message.html', sender='ai', message=ai_message)
    flask_response = make_response(response_html)

    # Inject HTMX Trigger for Navigation and Alerts
    nav_target = response.get('navigation')
    if nav_target:
        # Map internal route names to URLs
        route_map = {
            "index": url_for('main.index'),
            "employees": url_for('main.employees_list'),
            "projects": url_for('main.projects_list'),
            "tasks": url_for('main.tasks_list'),
            "systems": url_for('main.systems_list')
        }
        target_url = route_map.get(nav_target)

        # Handle dynamic project/system navigation (e.g., project:1, system:1)
        if not target_url and ":" in nav_target:
            parts = nav_target.split(":")
            if parts[0] == "project" and parts[1].isdigit():
                try:
                    target_url = url_for('main.tasks_list', f_project_id=int(parts[1]))
                except:
                    pass
            elif parts[0] == "system" and parts[1].isdigit():
                try:
                    target_url = url_for('main.system_detail', system_id=int(parts[1]))
                except:
                    pass

        if target_url:
            trigger_data["vision-navigation"] = {"target": target_url}

    if trigger_data:
        flask_response.headers["HX-Trigger"] = json.dumps(trigger_data)
        print(f"[Routes] HTMX Trigger set: {trigger_data}")

    return flask_response
@bp.route('/update-task/<int:task_id>', methods=['POST'])
def update_task_status(task_id):
    task = Task.query.get_or_404(task_id)

    # Handle Status Update
    new_status = request.form.get('status')
    if new_status in [s.value for s in StatusEnum]:
        task.status = StatusEnum(new_status)
        # A manually-set status bypasses the github_sync worker's active-task recheck (it only
        # ever revisits In-Progress/Testing Tasks), so any PR-review-state title color must be
        # cleared here too, or it would otherwise be orphaned forever.
        if task.status not in (StatusEnum.IN_PROGRESS, StatusEnum.TESTING):
            task.github_review_state = None

    # Handle Assignee Update
    new_assignee_id = request.form.get('employee_id')
    if new_assignee_id:
        if new_assignee_id == 'none':
            task.employee_id = None
        else:
            task.employee_id = int(new_assignee_id)

    # Handle Project Update
    new_project_id = request.form.get('project_id')
    if new_project_id:
        task.project_id = int(new_project_id)

    record_notification(f"Task '{task.name}' updated", 'success', employee_id=task.employee_id, task_id=task.id, project_id=task.project_id)
    db.session.commit()
    trigger_task_update(task_id)
    announcer.announce("update_tasks")

    # Return updated partial for HTMX
    if request.headers.get('HX-Request') == 'true':
        all_employees = Employee.query.all()

        # Extract filters from request (POST values from hx-include)
        q = request.values.get('f_q')
        status = request.values.get('f_status')
        system_id = request.values.get('f_system_id')
        employee_id = request.values.get('f_employee_id')
        project_id = request.values.get('f_project_id')

        query = Task.query.join(Project).filter(Project.status != StatusEnum.BLOCKED)
        if q:
            query = query.filter(Task.name.ilike(f'%{q}%'))
        if status and status != 'all':
            try:
                query = query.filter(Task.status == StatusEnum(status))
            except ValueError:
                pass
        if project_id and project_id != 'all':
            query = query.filter(Task.project_id == int(project_id))
        if employee_id and employee_id != 'all':
            if employee_id == 'none':
                query = query.filter(Task.employee_id == None)
            else:
                query = query.filter(Task.employee_id == int(employee_id))
        if system_id and system_id != 'all':
            query = query.filter(Project.system_id == int(system_id))

        tasks = sort_tasks(query.all())
        all_systems = System.query.all()
        all_projects = Project.query.all()
        flask_response = make_response(render_template('partials/_tasks_table.html',
                                                       tasks=tasks,
                                                       all_employees=all_employees,
                                                       all_systems=all_systems,
                                                       all_projects=all_projects,
                                                       statuses=StatusEnum,
                                                       f_q=q,
                                                       f_status=status,
                                                       f_system_id=system_id,
                                                       f_employee_id=employee_id,
                                                       f_project_id=project_id))

        # Success alert
        trigger_data = {"vision-alert": {"message": f"Task '{task.name}' updated", "type": "success"}}
        flask_response.headers["HX-Trigger"] = json.dumps(trigger_data)
        return flask_response

    return redirect(url_for('main.tasks_list', f_project_id=task.project_id))

@bp.route('/update-project/<int:project_id>', methods=['POST'])
def update_project_status(project_id):
    project = Project.query.get_or_404(project_id)

    # Handle Status Update
    new_status = request.form.get('status')
    if new_status in [s.value for s in StatusEnum]:
        project.status = StatusEnum(new_status)
        record_notification(f"Project '{project.name}' updated to {new_status}", 'success')
        db.session.commit()
        trigger_project_update(project_id)
        announcer.announce("update_projects")

    # Return updated partial for HTMX
    if request.headers.get('HX-Request') == 'true':
        refresh_type = request.args.get('refresh', 'projects')
        all_employees = Employee.query.all()

        if refresh_type == 'system' and project.system_id:
            system = System.query.get(project.system_id)
            flask_response = make_response(render_template('partials/_system_detail_content.html',
                                                           system=system,
                                                           all_employees=all_employees,
                                                           statuses=StatusEnum))
        else:
            projects = Project.query.all()
            flask_response = make_response(render_template('partials/_projects_table.html',
                                                           projects=projects,
                                                           all_employees=all_employees,
                                                           statuses=StatusEnum))
        # Success alert
        trigger_data = {"vision-alert": {"message": f"Project '{project.name}' updated to {new_status}", "type": "success"}}
        flask_response.headers["HX-Trigger"] = json.dumps(trigger_data)
        return flask_response

    return redirect(url_for('main.projects_list'))

def get_index_data():
    projects = Project.query.all()
    emp_count = Employee.query.count()
    sys_count = System.query.count()
    proj_count = Project.query.count()
    task_count = Task.query.count()

    analytics = [
        {"title": "Team", "value": str(emp_count), "trend": "Active Team", "trend_up": True, "icon": "bi-people-fill", "link": url_for('main.employees_list')},
        {"title": "Systems", "value": str(sys_count), "trend": "Organizations", "trend_up": True, "icon": "bi-diagram-3-fill", "link": url_for('main.systems_list')},
        {"title": "Projects", "value": str(proj_count), "trend": "Active Initiatives", "trend_up": True, "icon": "bi-folder-fill", "link": url_for('main.projects_list')},
        {"title": "Tasks", "value": str(task_count), "trend": "Open Issues", "trend_up": True, "icon": "bi-check-circle-fill", "link": url_for('main.tasks_list')}
    ]
    return projects, analytics

TASK_STATUS_ORDER = {
    StatusEnum.TESTING: 0,
    StatusEnum.IN_PROGRESS: 1,
    StatusEnum.TODO: 2,
    StatusEnum.REPEAT_DAILY: 3,
    StatusEnum.REPEAT_WEEKLY: 3,
    StatusEnum.REPEAT_MONTHLY: 3,
    StatusEnum.DONE: 4,
    StatusEnum.BLOCKED: 5,
}

# Fixed sentinel for the recency key. Deliberately NOT datetime.min: datetime.min.timestamp()
# raises ValueError on Linux (year 1 out of range), and leaving datetime.min here would be a
# landmine for anyone who later reaches for .timestamp().
_ORDER_EPOCH = datetime(1970, 1, 1)


def _to_naive_utc(dt):
    """Normalize for comparison. A single tz-aware value mixed with naive ones would raise
    TypeError mid-sort and 500 the whole Tasks page, so this guards inside the sort key --
    not only at the write boundary."""
    if dt is not None and dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _task_recency_key(task):
    """Newest-first key. ALWAYS used with reverse=True, so element 0 is the NULL policy:
    0 (no github_created_at) sorts LAST within its bucket, 1 sorts first.

    Cannot raise: no arithmetic, no .timestamp(), a fixed tuple shape of plain comparable
    datetimes/ints, and every datetime normalized to naive UTC first. Ends in task.id, so the
    key is a TOTAL order -- the result never depends on the DB's (unordered) row order.
    """
    github_created = _to_naive_utc(task.github_created_at)
    local_created = _to_naive_utc(task.created_at) or _ORDER_EPOCH
    # Issue number breaks same-second ties: GitHub's createdAt has 1-second resolution and
    # numbers issues monotonically per repo, so burst-created issues do collide.
    issue_number = task.github_issue_number or 0
    if github_created is None:
        return (0, _ORDER_EPOCH, issue_number, local_created, task.id or 0)
    return (1, github_created, issue_number, local_created, task.id or 0)


def sort_tasks(task_list):
    """Single ordering authority for the Tasks table. Two levels:
      1. status bucket: Testing -> In-Progress -> Todo -> Repeat_* -> Done -> Blocked
      2. within a bucket: newest GitHub issue first, by github_created_at DESC

    Two stable passes rather than one tuple key, because one key cannot mix an ascending
    field (status) with a descending one (recency) without negating a datetime. The three
    Tasks queries carry no order_by -- all ordering lives here, and _task_recency_key is a
    total order, so this does not rely on the DB returning rows in any particular order.

    Tasks with no github_created_at (created by hand, or an issue GitHub no longer returns)
    go to the END of their bucket rather than being interleaved on a fake date, which keeps
    the gap visible and self-correcting once sync populates the field.
    """
    by_recency = sorted(task_list, key=_task_recency_key, reverse=True)
    return sorted(by_recency, key=lambda t: TASK_STATUS_ORDER.get(t.status, 99))

@bp.route('/')
def index():
    projects, analytics = get_index_data()
    all_employees = Employee.query.all()
    notifications = Notification.query.order_by(Notification.created_at.desc()).limit(200).all()
    return render_template('index.html', projects=projects, analytics=analytics, all_employees=all_employees, statuses=StatusEnum, notifications=notifications)

@bp.route('/api/updates/index')
def api_index_updates():
    projects, analytics = get_index_data()
    return render_template('partials/_analytics_grid.html', analytics=analytics)

@bp.route('/api/updates/notifications')
def api_notifications_updates():
    notifications = Notification.query.order_by(Notification.created_at.desc()).limit(200).all()
    return render_template('partials/_notifications_panel.html', notifications=notifications)

@bp.route('/notifications/<int:notification_id>/delete', methods=['POST'])
def delete_notification(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    db.session.delete(notification)
    db.session.commit()
    return '', 200

@bp.route('/notifications/delete-all', methods=['POST'])
def delete_all_notifications():
    """Empties the whole Notification History panel in one request.

    Deliberately does NOT record_notification() its own action, unlike every other
    state-changing route in this module: that would immediately re-populate the list this
    button exists to empty, leaving exactly one "history cleared" row behind. The toast is
    sent as a display-only HX-Trigger instead, which never persists a row.

    Returns the re-rendered panel rather than delete_notification's `('', 200)` — with every
    row gone there is no single .notification-item left to slide out, so the caller swaps the
    whole card (hx-swap="outerHTML" onto .notifications-container, same shape as
    api_notifications_updates). Still a 200 *with a body*: htmx never swaps a 204.
    """
    deleted = Notification.query.delete()
    db.session.commit()
    announcer.announce("clear_notifications")

    # Re-queried instead of passing [] so a Notification written between the DELETE above and
    # this render (e.g. github_sync's 5s cadence) still appears, rather than being invisible
    # until the next SSE refresh.
    notifications = Notification.query.order_by(Notification.created_at.desc()).limit(200).all()
    response = make_response(render_template('partials/_notifications_panel.html', notifications=notifications))
    label = "notification" if deleted == 1 else "notifications"
    response.headers["HX-Trigger"] = json.dumps(
        {"vision-alert": {"message": f"Cleared {deleted} {label}", "type": "success"}}
    )
    return response

@bp.route('/employees')
def employees_list():
    employees = Employee.query.all()
    return render_template('employees.html', employees=employees)

@bp.route('/api/updates/employees')
def api_employees_updates():
    employees = Employee.query.all()
    return render_template('partials/_employees_table.html', employees=employees)

@bp.route('/projects')
def projects_list():
    projects = Project.query.all()
    all_employees = Employee.query.all()
    return render_template('projects.html', projects=projects, all_employees=all_employees, statuses=StatusEnum)

@bp.route('/api/updates/projects')
def api_projects_updates():
    projects = Project.query.all()
    all_employees = Employee.query.all()
    return render_template('partials/_projects_table.html', projects=projects,
                           all_employees=all_employees, statuses=StatusEnum,
                           table_title="All Initiatives",
                           table_subtitle="Detailed project portfolio and progress tracking")

@bp.route('/systems')
def systems_list():
    systems = System.query.all()
    return render_template('systems.html', systems=systems)

@bp.route('/systems/')
def systems_list_slash():
    return redirect(url_for('main.systems_list'))

@bp.route('/api/updates/systems')
def api_systems_updates():
    systems = System.query.all()
    return render_template('partials/_systems_table.html', systems=systems)

@bp.route('/tasks')
def tasks_list():
    # Retrieve optional system/project/assignee/search filters from query parameters
    system_id = request.args.get('f_system_id')
    project_id = request.args.get('f_project_id')
    employee_id = request.args.get('f_employee_id')
    q = request.args.get('f_q')
    query = Task.query.join(Project).filter(Project.status != StatusEnum.BLOCKED)
    if project_id and project_id != 'all':
        try:
            query = query.filter(Task.project_id == int(project_id))
        except ValueError:
            pass  # ignore invalid values
    if system_id and system_id != 'all':
        try:
            query = query.filter(Project.system_id == int(system_id))
        except ValueError:
            pass  # ignore invalid values
    if employee_id and employee_id != 'all':
        try:
            if employee_id == 'none':
                query = query.filter(Task.employee_id == None)
            else:
                query = query.filter(Task.employee_id == int(employee_id))
        except ValueError:
            pass  # ignore invalid values
    if q:
        query = query.filter(Task.name.ilike(f'%{q}%'))
    tasks = sort_tasks(query.all())
    all_employees = Employee.query.all()
    all_systems = System.query.all()
    all_projects = Project.query.all()
    return render_template('tasks.html',
                           tasks=tasks,
                           all_employees=all_employees,
                           all_systems=all_systems,
                           all_projects=all_projects,
                           statuses=StatusEnum,
                           f_system_id=system_id,
                           f_project_id=project_id,
                           f_employee_id=employee_id,
                           f_q=q)

@bp.route('/api/updates/tasks')
def api_tasks_updates():
    q = request.values.get('f_q')
    status = request.values.get('f_status')
    system_id = request.values.get('f_system_id')
    employee_id = request.values.get('f_employee_id')
    project_id = request.values.get('f_project_id')

    query = Task.query.join(Project).filter(Project.status != StatusEnum.BLOCKED)

    if q:
        query = query.filter(Task.name.ilike(f'%{q}%'))
    if status and status != 'all':
        try:
            query = query.filter(Task.status == StatusEnum(status))
        except ValueError:
            # Ignore invalid status
            pass
    if project_id and project_id != 'all':
        query = query.filter(Task.project_id == int(project_id))
    if employee_id and employee_id != 'all':
        if employee_id == 'none':
            query = query.filter(Task.employee_id == None)
        else:
            query = query.filter(Task.employee_id == int(employee_id))
    if system_id and system_id != 'all':
        query = query.filter(Project.system_id == int(system_id))

    tasks = sort_tasks(query.all())
    all_employees = Employee.query.all()
    all_systems = System.query.all()
    all_projects = Project.query.all()
    return render_template('partials/_tasks_table.html',
                           tasks=tasks,
                           all_employees=all_employees,
                           all_systems=all_systems,
                           all_projects=all_projects,
                           statuses=StatusEnum,
                           f_q=q,
                           f_status=status,
                           f_system_id=system_id,
                           f_employee_id=employee_id,
                           f_project_id=project_id)

@bp.route('/system/<int:system_id>')
def system_detail(system_id):
    system = System.query.get_or_404(system_id)
    all_employees = Employee.query.all()
    return render_template('system_detail.html', system=system, all_employees=all_employees, statuses=StatusEnum)

@bp.route('/api/updates/system/<int:system_id>')
def api_system_detail_updates(system_id):
    system = System.query.get_or_404(system_id)
    all_employees = Employee.query.all()
    return render_template('partials/_system_detail_content.html', system=system, all_employees=all_employees, statuses=StatusEnum)
