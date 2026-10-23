from datetime import datetime
from dashboard_app.app.extensions import db
from enum import Enum

class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class StatusEnum(Enum):
    TODO = "Todo"
    IN_PROGRESS = "In-Progress"
    TESTING = "Testing"
    DONE = "Done"
    BLOCKED = "Blocked"
    REPEAT_DAILY = "Repeat Daily"
    REPEAT_WEEKLY = "Repeat Weekly"
    REPEAT_MONTHLY = "Repeat Monthly"

class ReviewStateEnum(Enum):
    CHANGES_REQUESTED = "Changes Requested"
    CHANGES_APPLIED = "Changes Applied"

class Employee(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    tasks = db.relationship('Task', backref='assignee', lazy=True)

class System(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    github_org = db.Column(db.String(200), nullable=True)
    projects = db.relationship('Project', backref='system', lazy=True, cascade="all, delete-orphan")

    @property
    def github_url(self):
        if not self.github_org:
            return None
        return f"https://github.com/{self.github_org}"

class Project(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.Enum(StatusEnum), default=StatusEnum.TODO)
    github_repo = db.Column(db.String(200), nullable=True)
    system_id = db.Column(db.Integer, db.ForeignKey('system.id'), nullable=True)
    tasks = db.relationship('Task', backref='project', lazy=True, cascade="all, delete-orphan")

    @property
    def progress(self):
        if not self.tasks:
            return 0
        completed = [t for t in self.tasks if t.status == StatusEnum.DONE]
        return round((len(completed) / len(self.tasks)) * 100)

    @property
    def is_complete(self):
        return bool(self.tasks) and all(t.status == StatusEnum.DONE for t in self.tasks)

    @property
    def github_url(self):
        if not self.github_repo:
            return None
        return f"https://github.com/{self.github_repo}"

class Task(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.Enum(StatusEnum), default=StatusEnum.TODO)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)
    github_issue_number = db.Column(db.Integer, nullable=True)
    github_pr_number = db.Column(db.Integer, nullable=True)
    github_review_state = db.Column(db.Enum(ReviewStateEnum), nullable=True, default=None)
    # GitHub's own issue.createdAt, stored naive UTC to match TimestampMixin above.
    # NOT interchangeable with created_at: created_at is local row-insert time, and 206 of
    # 305 rows were inserted in bulk sync batches (102 inside 2026-08-24 10:34), where the
    # insertion order is GitHub's updatedAt DESC at sync time -- frozen forever, and useless
    # as a creation-order key. NULL means never synced: a manually created Task, or an issue
    # GitHub no longer returns. See docs/domains/business_logic.md.
    github_created_at = db.Column(db.DateTime, nullable=True)

    @property
    def review_state_class(self):
        if self.github_review_state == ReviewStateEnum.CHANGES_REQUESTED:
            return "task-title-changes-requested"
        if self.github_review_state == ReviewStateEnum.CHANGES_APPLIED:
            return "task-title-changes-applied"
        return None

    @property
    def github_url(self):
        repo = self.project.github_repo if self.project else None
        if not repo:
            return None
        if self.github_pr_number:
            return f"https://github.com/{repo}/pull/{self.github_pr_number}"
        if self.github_issue_number:
            return f"https://github.com/{repo}/issues/{self.github_issue_number}"
        return None

    @property
    def github_issue_url(self):
        repo = self.project.github_repo if self.project else None
        if not repo or not self.github_issue_number:
            return None
        return f"https://github.com/{repo}/issues/{self.github_issue_number}"

    @property
    def github_pr_url(self):
        repo = self.project.github_repo if self.project else None
        if not repo or not self.github_pr_number:
            return None
        return f"https://github.com/{repo}/pull/{self.github_pr_number}"

class PlanStatusEnum(Enum):
    # Values double as CSS class suffixes (no spaces), unlike StatusEnum. Names follow the
    # status-color rule of the plan documents this feature imports (sinpr/conpr/...).
    NO_PR = "sinpr"
    PR_OPEN = "conpr"
    PR_BLOCKED = "prbloq"
    MERGED = "fusionada"
    CLOSED = "cerrada"
    NOT_PLANNED = "descartada"

# Plan-complete statuses for progress: the PM decision (2026-10-22) counts a merged PR as done
# even while its issue stays open for staging verification. NOT_PLANNED leaves the denominator.
PLAN_DONE_STATUSES = (PlanStatusEnum.MERGED, PlanStatusEnum.CLOSED)

class Plan(db.Model, TimestampMixin):
    """A short-cycle implementation plan: the subset of a System's GitHub issues that counts
    toward progress right now, plus their dependency DAG. At most one active Plan per System
    (enforced in execution/plan_import.py, not by a constraint)."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    system_id = db.Column(db.Integer, db.ForeignKey('system.id'), nullable=False)
    system = db.relationship('System')
    target_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=False)
    source_name = db.Column(db.String(255), nullable=True)
    spec_json = db.Column(db.Text, nullable=False)
    items = db.relationship('PlanItem', backref='plan', lazy=True, cascade="all, delete-orphan",
                            order_by='PlanItem.position')
    edges = db.relationship('PlanEdge', backref='plan', lazy=True, cascade="all, delete-orphan",
                            order_by='PlanEdge.position')

class PlanItem(db.Model, TimestampMixin):
    """One node of a Plan's graph. node_kind 'issue' mirrors a GitHub issue (live state below,
    written only by execution/plan_sync.py); 'base' is a branch context node with no issue."""
    __table_args__ = (
        db.UniqueConstraint('plan_id', 'key', name='uq_plan_item_key'),
        db.UniqueConstraint('plan_id', 'repo', 'issue_number', name='uq_plan_item_issue'),
    )
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plan.id'), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    key = db.Column(db.String(50), nullable=False)
    display_key = db.Column(db.String(50), nullable=True)
    label = db.Column(db.String(200), nullable=True)
    group_key = db.Column(db.String(50), nullable=False)
    group_label = db.Column(db.String(200), nullable=True)
    repo = db.Column(db.String(200), nullable=True)
    issue_number = db.Column(db.Integer, nullable=True)
    node_kind = db.Column(db.String(10), nullable=False, default='issue')
    task_id = db.Column(db.Integer, db.ForeignKey('task.id', ondelete='SET NULL'), nullable=True)
    task = db.relationship('Task')
    github_title = db.Column(db.String(300), nullable=True)
    issue_state = db.Column(db.String(20), nullable=True)
    issue_state_reason = db.Column(db.String(20), nullable=True)
    pr_number = db.Column(db.Integer, nullable=True)
    pr_state = db.Column(db.String(20), nullable=True)
    pr_is_draft = db.Column(db.Boolean, nullable=True)
    pr_ci_state = db.Column(db.String(20), nullable=True)
    pr_review_decision = db.Column(db.String(30), nullable=True)
    plan_status = db.Column(db.Enum(PlanStatusEnum), nullable=True)
    status_changed_at = db.Column(db.DateTime, nullable=True)
    last_synced_at = db.Column(db.DateTime, nullable=True)

    @property
    def issue_url(self):
        if not self.repo or not self.issue_number:
            return None
        return f"https://github.com/{self.repo}/issues/{self.issue_number}"

    @property
    def pr_url(self):
        if not self.repo or not self.pr_number:
            return None
        return f"https://github.com/{self.repo}/pull/{self.pr_number}"

class PlanEdge(db.Model):
    """kind: 'base' (starts from the base branch), 'stacked' (PR targets the parent's branch),
    'after_merge' (starts from main once the parent is merged), 'cross' (cross-repo condition)."""
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plan.id'), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    from_key = db.Column(db.String(50), nullable=False)
    to_key = db.Column(db.String(50), nullable=False)
    kind = db.Column(db.String(20), nullable=False)
    label = db.Column(db.String(100), nullable=True)

class ChatMessage(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'ai'
    content = db.Column(db.Text, nullable=False)

class Notification(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(20), nullable=False, default='info')  # mirrors toast type
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)
    employee = db.relationship('Employee')
    # task_id/project_id are a snapshot captured at event time (not a live lookup), so the
    # notification still displays/links sensibly even if the Task is later deleted.
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    # Unlike task_id/project_id above, the Task's title is looked up live (not snapshotted) when
    # building the "jump to this task" link, so a since-renamed Task still gets found by search.
    task = db.relationship('Task')

# The Notification History keeps only the newest rows; every insert prunes the rest.
NOTIFICATION_HISTORY_LIMIT = 500

def prune_notifications(session, keep=NOTIFICATION_HISTORY_LIMIT):
    """Deletes every Notification older than the `keep` newest, ordered by id (insertion order).

    Works with any SQLAlchemy session (Flask's db.session or execution's get_session()) and
    does not commit, so it rides the same transaction as the insert that triggered it.
    Returns the number of rows deleted."""
    cutoff = (session.query(Notification.id)
              .order_by(Notification.id.desc())
              .offset(keep - 1).limit(1).scalar())
    if cutoff is None:
        return 0
    return (session.query(Notification)
            .filter(Notification.id < cutoff)
            .delete(synchronize_session=False))
