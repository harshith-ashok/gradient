"""admin monitoring: log entries and issues

Revision ID: 0006
Revises: 0005
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "log_entries",
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("level", sa.String(length=10), nullable=False),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.Column("logger", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("method", sa.String(length=8), nullable=True),
        sa.Column("path", sa.String(length=255), nullable=True),
        sa.Column("status", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.String(length=40), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=True),
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.CheckConstraint("level IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL')", name="ck_log_entries_level"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_log_entries_ts", "log_entries", ["ts"])
    op.create_index("ix_log_entries_level", "log_entries", ["level"])
    op.create_index("ix_log_entries_request_id", "log_entries", ["request_id"])
    op.create_table(
        "issues",
        sa.Column("fingerprint", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("exc_type", sa.String(length=120), nullable=False),
        sa.Column("culprit", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.CheckConstraint("status IN ('open', 'resolved', 'ignored')", name="ck_issues_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint"),
    )
    op.create_index("ix_issues_status", "issues", ["status"])
    op.create_index("ix_issues_last_seen", "issues", ["last_seen"])
    op.create_table(
        "issue_events",
        sa.Column("issue_id", sa.String(length=40), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("stack_trace", sa.Text(), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("method", sa.String(length=8), nullable=True),
        sa.Column("path", sa.String(length=255), nullable=True),
        sa.Column("user_id", sa.String(length=40), nullable=True),
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_issue_events_issue_id", "issue_events", ["issue_id"])
    op.create_index("ix_issue_events_ts", "issue_events", ["ts"])


def downgrade() -> None:
    op.drop_table("issue_events")
    op.drop_table("issues")
    op.drop_table("log_entries")
