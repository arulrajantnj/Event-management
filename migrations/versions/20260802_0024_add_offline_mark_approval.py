"""add offline mark approval workflow

Revision ID: 20260802_0024
Revises: 20260801_0023
"""
from alembic import op
import sqlalchemy as sa


revision = "20260802_0024"
down_revision = "20260801_0023"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("offline_exam_marks", sa.Column("approval_status", sa.String(20), nullable=False, server_default="draft"))
    op.add_column("offline_exam_marks", sa.Column("approved_by", sa.String(120)))
    op.add_column("offline_exam_marks", sa.Column("approved_datetime", sa.DateTime()))
    op.add_column("offline_exam_marks", sa.Column("approval_notes", sa.Text(), server_default=""))
    op.create_index("ix_offline_exam_marks_approval_status", "offline_exam_marks", ["approval_status"])


def downgrade():
    op.drop_index("ix_offline_exam_marks_approval_status", table_name="offline_exam_marks")
    op.drop_column("offline_exam_marks", "approval_notes")
    op.drop_column("offline_exam_marks", "approved_datetime")
    op.drop_column("offline_exam_marks", "approved_by")
    op.drop_column("offline_exam_marks", "approval_status")
