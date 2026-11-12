"""learning engine

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('quiz_sessions',
    sa.Column('user_id', sa.String(length=40), nullable=False),
    sa.Column('course_id', sa.String(length=40), nullable=False),
    sa.Column('kind', sa.String(length=10), nullable=False),
    sa.Column('topic_id', sa.String(length=40), nullable=True),
    sa.Column('subtopic_id', sa.String(length=40), nullable=True),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('scope', sa.String(length=255), nullable=False),
    sa.Column('questions', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.String(length=40), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_sessions_user_id'), 'quiz_sessions', ['user_id'], unique=False)
    op.create_table('day_statuses',
    sa.Column('enrollment_id', sa.String(length=40), nullable=False),
    sa.Column('day_index', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('mastery', sa.Integer(), nullable=False),
    sa.Column('message', sa.String(length=120), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.String(length=40), nullable=False),
    sa.ForeignKeyConstraint(['enrollment_id'], ['enrollments.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('enrollment_id', 'day_index', name='uq_day_status')
    )
    op.create_index(op.f('ix_day_statuses_enrollment_id'), 'day_statuses', ['enrollment_id'], unique=False)
    op.create_table('plan_notices',
    sa.Column('enrollment_id', sa.String(length=40), nullable=False),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.String(length=40), nullable=False),
    sa.ForeignKeyConstraint(['enrollment_id'], ['enrollments.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_plan_notices_enrollment_id'), 'plan_notices', ['enrollment_id'], unique=False)
    JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
    # Batch mode so the same migration runs on SQLite (tests) and Postgres.
    with op.batch_alter_table("enrollments") as b:
        b.add_column(sa.Column("plan_start_date", sa.Date(), nullable=False,
                               server_default=sa.text("CURRENT_DATE")))
        b.add_column(sa.Column("pretest_score", sa.Float(), nullable=True))
    with op.batch_alter_table("mastery") as b:
        b.add_column(sa.Column("last_score", sa.Float(), nullable=True))
        b.add_column(sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
        b.add_column(sa.Column("studied", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("plan_tasks") as b:
        b.add_column(sa.Column("title", sa.String(length=255), nullable=False, server_default=""))
        b.add_column(sa.Column("day_index", sa.Integer(), nullable=False, server_default="0"))
        b.add_column(sa.Column("result", sa.String(length=80), nullable=True))
        b.drop_constraint("ck_plan_tasks_type", type_="check")
        b.create_check_constraint(
            "ck_plan_tasks_type",
            "type IN ('study', 'quiz', 'confirm', 'remediation', 'retake', 'topic_quiz')",
        )
    with op.batch_alter_table("quiz_attempts") as b:
        b.add_column(sa.Column("title", sa.String(length=255), nullable=False, server_default=""))
        b.add_column(sa.Column("correct", sa.Integer(), nullable=False, server_default="0"))
        b.add_column(sa.Column("total", sa.Integer(), nullable=False, server_default="0"))
        b.add_column(sa.Column("breakdown", JSON, nullable=False, server_default=sa.text("'[]'")))
        b.alter_column("pass_mark", existing_type=sa.Integer(), nullable=True)
        b.alter_column("passed", existing_type=sa.Boolean(), nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    with op.batch_alter_table("quiz_attempts") as b:
        b.alter_column("passed", existing_type=sa.Boolean(), nullable=False)
        b.alter_column("pass_mark", existing_type=sa.Integer(), nullable=False)
        for c in ("breakdown", "total", "correct", "title"):
            b.drop_column(c)
    with op.batch_alter_table("plan_tasks") as b:
        b.drop_constraint("ck_plan_tasks_type", type_="check")
        b.create_check_constraint(
            "ck_plan_tasks_type", "type IN ('study', 'quiz', 'remediation', 'topic_quiz')"
        )
        for c in ("result", "day_index", "title"):
            b.drop_column(c)
    with op.batch_alter_table("mastery") as b:
        for c in ("studied", "attempts", "last_score"):
            b.drop_column(c)
    with op.batch_alter_table("enrollments") as b:
        b.drop_column("pretest_score")
        b.drop_column("plan_start_date")
    op.drop_index(op.f("ix_plan_notices_enrollment_id"), table_name="plan_notices")
    op.drop_table("plan_notices")
    op.drop_index(op.f("ix_day_statuses_enrollment_id"), table_name="day_statuses")
    op.drop_table("day_statuses")
    op.drop_index(op.f("ix_quiz_sessions_user_id"), table_name="quiz_sessions")
    op.drop_table("quiz_sessions")
