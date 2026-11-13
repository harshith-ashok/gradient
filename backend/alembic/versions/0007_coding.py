"""coding challenges: problems and submissions

Revision ID: 0007
Revises: 0006
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "coding_problems",
        sa.Column("subtopic_id", sa.String(length=40), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("languages", JSON, nullable=False),
        sa.Column("starter", JSON, nullable=False),
        sa.Column("time_limit_ms", sa.Integer(), nullable=False),
        sa.Column("memory_mb", sa.Integer(), nullable=False),
        sa.Column("tests", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.CheckConstraint("level IN ('beginner', 'intermediate', 'advanced', 'expert')", name="ck_coding_problems_level"),
        sa.ForeignKeyConstraint(["subtopic_id"], ["subtopics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coding_problems_subtopic_id", "coding_problems", ["subtopic_id"])
    op.create_table(
        "code_submissions",
        sa.Column("problem_id", sa.String(length=40), nullable=False),
        sa.Column("user_id", sa.String(length=40), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("mode", sa.String(length=8), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=8), nullable=False),
        sa.Column("verdict", sa.String(length=16), nullable=True),
        sa.Column("passed", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("runtime_ms", sa.Integer(), nullable=True),
        sa.Column("compile_output", sa.Text(), nullable=True),
        sa.Column("results", JSON, nullable=False),
        sa.Column("message", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.CheckConstraint("mode IN ('run', 'submit', 'check')", name="ck_code_submissions_mode"),
        sa.CheckConstraint("state IN ('queued', 'running', 'done')", name="ck_code_submissions_state"),
        sa.ForeignKeyConstraint(["problem_id"], ["coding_problems.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_code_submissions_problem_id", "code_submissions", ["problem_id"])
    op.create_index("ix_code_submissions_user_id", "code_submissions", ["user_id"])
    op.create_index("ix_code_submissions_state", "code_submissions", ["state"])
    op.create_index("ix_code_submissions_created_at", "code_submissions", ["created_at"])


def downgrade() -> None:
    op.drop_table("code_submissions")
    op.drop_table("coding_problems")
