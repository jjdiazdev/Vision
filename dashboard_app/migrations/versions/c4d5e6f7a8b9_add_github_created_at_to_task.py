"""add github_created_at to task

Stores GitHub's own issue.createdAt so the Tasks table can order newest-issue-first within
each status bucket. The local `created_at` cannot serve that purpose: most rows were inserted
in bulk sync batches, so their insertion order encodes GitHub's updatedAt DESC at sync time.

Schema only -- this migration does NOT populate the column, deliberately: the web
container's entrypoint runs `flask db upgrade` on every boot, so a data migration needing
the GitHub API would make app startup depend on network and a token. Populate it with:

    docker exec vision-web-1 python -m execution.backfill_github_created_at --dry-run
    docker exec vision-web-1 python -m execution.backfill_github_created_at

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c4d5e6f7a8b9'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    # Keep this a SINGLE add_column: that op is natively supported, so batch mode emits a
    # plain ALTER TABLE ADD COLUMN and leaves the enum column and FKs untouched. Folding
    # another op in here would switch Alembic to a table copy/recreate.
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('github_created_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.drop_column('github_created_at')
