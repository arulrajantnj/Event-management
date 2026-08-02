"""add hybrid offline examination tables

Revision ID: 20260801_0023
Revises: 20260801_0022
"""
from alembic import op
import sqlalchemy as sa

revision = "20260801_0023"
down_revision = "20260801_0022"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("exam_mode_selection", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False), sa.Column("exam_id", sa.Integer(), sa.ForeignKey("online_exams.id"), nullable=False), sa.Column("mode", sa.String(10), nullable=False), sa.Column("selected_datetime", sa.DateTime(), nullable=False), sa.Column("submitted", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("ip_address", sa.String(64)), sa.UniqueConstraint("student_id", "exam_id", name="uq_exam_mode_student_exam"))
    op.create_table("offline_exam_students", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("exam_id", sa.Integer(), sa.ForeignKey("online_exams.id"), nullable=False), sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False), sa.Column("school_udise", sa.String(30), nullable=False), sa.Column("mentor_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("selected_datetime", sa.DateTime(), nullable=False), sa.UniqueConstraint("exam_id", "student_id", name="uq_offline_exam_student"))
    op.create_table("offline_exam_attendance", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("offline_exam_student_id", sa.Integer(), sa.ForeignKey("offline_exam_students.id"), nullable=False), sa.Column("attendance_status", sa.String(10), nullable=False), sa.Column("marked_at", sa.DateTime(), nullable=False), sa.UniqueConstraint("offline_exam_student_id", name="uq_offline_attendance_student"))
    op.create_table("offline_exam_marks", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("exam_id", sa.Integer(), sa.ForeignKey("online_exams.id"), nullable=False), sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False), sa.Column("school_udise", sa.String(30), nullable=False), sa.Column("mentor_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False), sa.Column("max_marks", sa.Float(), nullable=False), sa.Column("obtained_marks", sa.Float(), nullable=False), sa.Column("percentage", sa.Float(), nullable=False), sa.Column("result", sa.String(10)), sa.Column("remarks", sa.Text()), sa.Column("submitted", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("submitted_datetime", sa.DateTime()), sa.UniqueConstraint("exam_id", "student_id", name="uq_offline_mark_student"))
    op.create_table("questionpaper_download_log", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("exam_id", sa.Integer(), sa.ForeignKey("online_exams.id"), nullable=False), sa.Column("school_udise", sa.String(30), nullable=False), sa.Column("mentor_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False), sa.Column("download_datetime", sa.DateTime(), nullable=False), sa.Column("ip_address", sa.String(64)), sa.UniqueConstraint("exam_id", "school_udise", name="uq_question_paper_school"))
    op.create_table("offline_exam_audit_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("exam_id", sa.Integer(), sa.ForeignKey("online_exams.id"), nullable=False), sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id")), sa.Column("action", sa.String(80), nullable=False), sa.Column("details", sa.Text()), sa.Column("actor", sa.String(120)), sa.Column("created_at", sa.DateTime(), nullable=False))


def downgrade():
    op.drop_table("offline_exam_audit_logs"); op.drop_table("questionpaper_download_log"); op.drop_table("offline_exam_marks"); op.drop_table("offline_exam_attendance"); op.drop_table("offline_exam_students"); op.drop_table("exam_mode_selection")
