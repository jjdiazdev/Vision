"""add plan, plan_item and plan_edge tables

A Plan scopes progress to the GitHub issues of the current short-cycle implementation plan and
stores its dependency DAG. Schema only: plans are imported with
`python -m execution.agent_actions plan --import <file.json>`, and their live GitHub state is
filled in by the github-sync worker (execution/plan_sync.py), never by this migration.

New tables only -- no existing table is altered, so no batch-mode table copy is involved.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-10-22
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd5e6f7a8b9c0'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None

PLAN_STATUS = sa.Enum('NO_PR', 'PR_OPEN', 'PR_BLOCKED', 'MERGED', 'CLOSED', 'NOT_PLANNED',
                      name='planstatusenum')


def upgrade():
    op.create_table('plan',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('system_id', sa.Integer(), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('source_name', sa.String(length=255), nullable=True),
        sa.Column('spec_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['system_id'], ['system.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('plan_item',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=50), nullable=False),
        sa.Column('display_key', sa.String(length=50), nullable=True),
        sa.Column('label', sa.String(length=200), nullable=True),
        sa.Column('group_key', sa.String(length=50), nullable=False),
        sa.Column('group_label', sa.String(length=200), nullable=True),
        sa.Column('repo', sa.String(length=200), nullable=True),
        sa.Column('issue_number', sa.Integer(), nullable=True),
        sa.Column('node_kind', sa.String(length=10), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('github_title', sa.String(length=300), nullable=True),
        sa.Column('issue_state', sa.String(length=20), nullable=True),
        sa.Column('issue_state_reason', sa.String(length=20), nullable=True),
        sa.Column('pr_number', sa.Integer(), nullable=True),
        sa.Column('pr_state', sa.String(length=20), nullable=True),
        sa.Column('pr_is_draft', sa.Boolean(), nullable=True),
        sa.Column('pr_ci_state', sa.String(length=20), nullable=True),
        sa.Column('pr_review_decision', sa.String(length=30), nullable=True),
        sa.Column('plan_status', PLAN_STATUS, nullable=True),
        sa.Column('status_changed_at', sa.DateTime(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['plan.id'], ),
        sa.ForeignKeyConstraint(['task_id'], ['task.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plan_id', 'key', name='uq_plan_item_key'),
        sa.UniqueConstraint('plan_id', 'repo', 'issue_number', name='uq_plan_item_issue')
    )
    op.create_table('plan_edge',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('from_key', sa.String(length=50), nullable=False),
        sa.Column('to_key', sa.String(length=50), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['plan.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('plan_edge')
    op.drop_table('plan_item')
    op.drop_table('plan')
