"""time frame for study plans and plan jobs

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("enrollments") as b:
        b.add_column(sa.Column("target_days", sa.Integer(), nullable=False, server_default="21"))
    with op.batch_alter_table("plan_tasks") as b:
        b.add_column(sa.Column("note", sa.String(length=200), nullable=True))
    with op.batch_alter_table("jobs") as b:
        b.add_column(sa.Column("enrollment_id", sa.String(length=40), nullable=True))
        b.create_foreign_key("fk_jobs_enrollment", "enrollments", ["enrollment_id"], ["id"], ondelete="CASCADE")
        b.create_index("ix_jobs_enrollment_id", ["enrollment_id"])
        b.drop_constraint("ck_jobs_type", type_="check")
        b.create_check_constraint("ck_jobs_type", "type IN ('analyze', 'derive', 'generate', 'plan')")


def downgrade() -> None:
    with op.batch_alter_table("jobs") as b:
        b.drop_constraint("ck_jobs_type", type_="check")
        b.create_check_constraint("ck_jobs_type", "type IN ('analyze', 'derive', 'generate')")
        b.drop_index("ix_jobs_enrollment_id")
        b.drop_constraint("fk_jobs_enrollment", type_="foreignkey")
        b.drop_column("enrollment_id")
    with op.batch_alter_table("plan_tasks") as b:
        b.drop_column("note")
    with op.batch_alter_table("enrollments") as b:
        b.drop_column("target_days")
