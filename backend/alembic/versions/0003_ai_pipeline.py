"""ai pipeline

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('jobs',
    sa.Column('type', sa.String(length=16), nullable=False),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.Column('created_by', sa.String(length=40), nullable=False),
    sa.Column('course_id', sa.String(length=40), nullable=True),
    sa.Column('upload_id', sa.String(length=40), nullable=True),
    sa.Column('params', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('progress', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('result', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.String(length=40), nullable=False),
    sa.CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed')", name='ck_jobs_status'),
    sa.CheckConstraint("type IN ('analyze', 'derive', 'generate')", name='ck_jobs_type'),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['upload_id'], ['syllabus_uploads.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_jobs_course_id'), 'jobs', ['course_id'], unique=False)
    op.create_index(op.f('ix_jobs_created_at'), 'jobs', ['created_at'], unique=False)
    op.create_index(op.f('ix_jobs_created_by'), 'jobs', ['created_by'], unique=False)
    op.create_index(op.f('ix_jobs_status'), 'jobs', ['status'], unique=False)
    op.create_index(op.f('ix_jobs_upload_id'), 'jobs', ['upload_id'], unique=False)
    JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
    with op.batch_alter_table("syllabus_uploads") as b:  # batch mode: runs on SQLite (tests) and Postgres
        b.add_column(sa.Column("uploader_id", sa.String(length=40), nullable=True))
        b.add_column(sa.Column("ocr_used", sa.Boolean(), nullable=False, server_default=sa.false()))
        b.add_column(sa.Column("indexed", sa.Boolean(), nullable=False, server_default=sa.false()))
        b.add_column(sa.Column("topics", JSON, nullable=True))
        b.create_foreign_key(
            "fk_syllabus_uploads_uploader", "users", ["uploader_id"], ["id"], ondelete="SET NULL"
        )
    # ### end Alembic commands ###


def downgrade() -> None:
    with op.batch_alter_table("syllabus_uploads") as b:
        b.drop_constraint("fk_syllabus_uploads_uploader", type_="foreignkey")
        for c in ("topics", "indexed", "ocr_used", "uploader_id"):
            b.drop_column(c)
    for ix in ("upload_id", "status", "created_by", "created_at", "course_id"):
        op.drop_index(op.f(f"ix_jobs_{ix}"), table_name="jobs")
    op.drop_table("jobs")
