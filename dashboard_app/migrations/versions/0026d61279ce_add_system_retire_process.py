"""add system model, migrate task/project hierarchy off process

Revision ID: 0026d61279ce
Revises: ab025a305c3e
Create Date: 2026-08-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0026d61279ce'
down_revision = 'ab025a305c3e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('system',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('github_org', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.add_column(sa.Column('system_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_project_system_id', 'system', ['system_id'], ['id'])

    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('project_id', sa.Integer(), nullable=True))

    conn = op.get_bind()

    # One System per distinct org parsed from existing project.github_repo ("owner/repo")
    orgs = conn.execute(sa.text(
        "SELECT DISTINCT substr(github_repo, 1, instr(github_repo, '/') - 1) AS org "
        "FROM project WHERE github_repo IS NOT NULL AND github_repo LIKE '%/%'"
    )).fetchall()
    for (org,) in orgs:
        conn.execute(sa.text(
            "INSERT INTO system (name, github_org, created_at, updated_at) "
            "VALUES (:org, :org, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ), {"org": org})

    conn.execute(sa.text(
        "UPDATE project SET system_id = ("
        "  SELECT s.id FROM system s "
        "  WHERE s.github_org = substr(project.github_repo, 1, instr(project.github_repo, '/') - 1)"
        ") WHERE github_repo IS NOT NULL AND github_repo LIKE '%/%'"
    ))

    # Every existing Task collapses onto its (former) process's project directly
    conn.execute(sa.text(
        "UPDATE task SET project_id = ("
        "  SELECT p.project_id FROM process p WHERE p.id = task.process_id"
        ")"
    ))

    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.alter_column('project_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key('fk_task_project_id', 'project', ['project_id'], ['id'])
        batch_op.drop_column('process_id')

    op.drop_table('process')


def downgrade():
    # Schema shape only -- Process-level Task grouping and System derivation are NOT
    # reconstructible (that data was collapsed in upgrade()). A true rollback needs a
    # pre-migration DB backup; none is retained in this repo as of 2026-08-27 (the original
    # backup taken before this migration ran was deleted once verified) -- take a fresh one
    # before running this downgrade against a populated database.
    op.create_table('process',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('process_id', sa.Integer(), nullable=True))
        batch_op.drop_constraint('fk_task_project_id', type_='foreignkey')
        batch_op.drop_column('project_id')

    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.drop_constraint('fk_project_system_id', type_='foreignkey')
        batch_op.drop_column('system_id')

    op.drop_table('system')
