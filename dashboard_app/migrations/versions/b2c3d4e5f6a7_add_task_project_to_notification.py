"""add task_id and project_id to notification

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.add_column(sa.Column('task_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('project_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_notification_task_id', 'task', ['task_id'], ['id'])
        batch_op.create_foreign_key('fk_notification_project_id', 'project', ['project_id'], ['id'])


def downgrade():
    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.drop_constraint('fk_notification_project_id', type_='foreignkey')
        batch_op.drop_constraint('fk_notification_task_id', type_='foreignkey')
        batch_op.drop_column('project_id')
        batch_op.drop_column('task_id')
