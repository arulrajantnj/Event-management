"""upgrade online exam attempt lifecycle and proctoring

Revision ID: 20260720_0017
Revises: 20260712_0016
"""
from alembic import op
import sqlalchemy as sa


revision = "20260720_0017"
down_revision = "20260712_0016"
branch_labels = None
depends_on = None


def columns(table):
    return {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def add_missing(table, additions):
    existing = columns(table)
    for name, column in additions:
        if name not in existing:
            op.add_column(table, column)


def upgrade():
    existing_tables = tables()
    add_missing("online_exams", [
        ("randomize_questions", sa.Column("randomize_questions", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("shuffle_options", sa.Column("shuffle_options", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("question_count", sa.Column("question_count", sa.Integer())),
        ("webcam_proctoring", sa.Column("webcam_proctoring", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("webcam_capture_interval", sa.Column("webcam_capture_interval", sa.Integer(), nullable=False, server_default="60")),
    ])

    if "exam_question_pools" not in existing_tables:
        op.create_table(
            "exam_question_pools",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("exam_id", sa.Integer(), sa.ForeignKey("online_exams.id"), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("questions_to_draw", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("exam_id", "name", name="uq_exam_question_pool_name"),
        )

    pool_column = (
        sa.Column("pool_id", sa.Integer())
        if op.get_bind().dialect.name == "sqlite"
        else sa.Column("pool_id", sa.Integer(), sa.ForeignKey("exam_question_pools.id"))
    )
    add_missing("exam_questions", [("pool_id", pool_column)])
    add_missing("exam_attempts", [
        ("status", sa.Column("status", sa.String(20), nullable=False, server_default="submitted")),
        ("deadline_at", sa.Column("deadline_at", sa.DateTime())),
        ("question_order_json", sa.Column("question_order_json", sa.Text())),
        ("option_order_json", sa.Column("option_order_json", sa.Text())),
        ("last_saved_at", sa.Column("last_saved_at", sa.DateTime())),
    ])
    add_missing("exam_answers", [
        ("marked_for_review", sa.Column("marked_for_review", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("saved_at", sa.Column("saved_at", sa.DateTime())),
    ])

    if "exam_proctoring_snapshots" not in existing_tables:
        op.create_table(
            "exam_proctoring_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("attempt_id", sa.Integer(), sa.ForeignKey("exam_attempts.id"), nullable=False),
            sa.Column("file_path", sa.String(500), nullable=False),
            sa.Column("capture_type", sa.String(30), nullable=False, server_default="periodic"),
            sa.Column("captured_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_exam_proctoring_attempt", "exam_proctoring_snapshots", ["attempt_id", "captured_at"])

    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes("exam_answers")}
    if "uq_exam_answer_attempt_question" not in indexes:
        op.create_index("uq_exam_answer_attempt_question", "exam_answers", ["attempt_id", "question_id"], unique=True)


def downgrade():
    pass
