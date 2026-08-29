"""add notification table

Revision ID: a1b2c3d4e5f6
Revises: f3a9c1d7b204
Create Date: 2026-08-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f3a9c1d7b204'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('notification',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['employee.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('notification')
