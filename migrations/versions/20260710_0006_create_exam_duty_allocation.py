"""create exam duty allocation tables

Revision ID: 20260710_0006
Revises: 20260710_0005
Create Date: 2026-07-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "20260710_0006"
down_revision = "20260710_0005"
branch_labels = None
depends_on = None


def table_names():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade():
    existing = table_names()
    if "exam_duty_teachers" not in existing:
        op.create_table(
            "exam_duty_teachers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
            sa.Column("teacher_id", sa.String(length=80), nullable=False),
            sa.Column("teacher_name", sa.String(length=150), nullable=False),
            sa.Column("mobile", sa.String(length=20)),
            sa.Column("designation", sa.String(length=120)),
            sa.Column("working_school", sa.String(length=220)),
            sa.Column("udise_code", sa.String(length=30)),
            sa.Column("working_block", sa.String(length=120)),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime()),
            sa.UniqueConstraint("event_id", "teacher_id", name="uq_exam_duty_teacher_event_id"),
        )
    if "exam_duty_centers" not in existing:
        op.create_table(
            "exam_duty_centers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
            sa.Column("center_name", sa.String(length=220), nullable=False),
            sa.Column("center_no", sa.String(length=80), nullable=False),
            sa.Column("center_block", sa.String(length=120), nullable=False),
            sa.Column("invigilators_required", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime()),
            sa.UniqueConstraint("event_id", "center_no", name="uq_exam_duty_center_number"),
        )
    if "exam_duty_allocations" not in existing:
        op.create_table(
            "exam_duty_allocations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
            sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("exam_duty_teachers.id"), nullable=False),
            sa.Column("center_id", sa.Integer(), sa.ForeignKey("exam_duty_centers.id"), nullable=False),
            sa.Column("allocation_method", sa.String(length=20), nullable=False, server_default="manual"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
            sa.Column("created_at", sa.DateTime()),
            sa.UniqueConstraint("event_id", "teacher_id", name="uq_exam_duty_teacher_allocation"),
        )


def downgrade():
    existing = table_names()
    for name in ("exam_duty_allocations", "exam_duty_centers", "exam_duty_teachers"):
        if name in existing:
            op.drop_table(name)
