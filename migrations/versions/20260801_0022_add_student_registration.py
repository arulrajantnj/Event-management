"""add student registration and approval tables

Revision ID: 20260801_0022
Revises: 20260723_0021
"""
from alembic import op
import sqlalchemy as sa


revision = "20260801_0022"
down_revision = "20260723_0021"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("registration_settings", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("field_name", sa.String(50), nullable=False, unique=True), sa.Column("field_label", sa.String(120), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    op.create_table("custom_registration_questions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("label", sa.String(180), nullable=False), sa.Column("field_name", sa.String(80), nullable=False, unique=True), sa.Column("question_type", sa.String(20), nullable=False), sa.Column("placeholder", sa.String(180)), sa.Column("default_value", sa.Text()), sa.Column("options", sa.Text()), sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("students", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("registration_no", sa.String(30), nullable=False, unique=True), sa.Column("student_name", sa.String(180), nullable=False), sa.Column("student_class", sa.String(40)), sa.Column("section", sa.String(40)), sa.Column("emis_no", sa.String(30), unique=True), sa.Column("udise_no", sa.String(30)), sa.Column("school_name", sa.String(220)), sa.Column("mobile", sa.String(15), unique=True), sa.Column("medium", sa.String(20)), sa.Column("username", sa.String(80), nullable=False, unique=True), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("approval_status", sa.String(20), nullable=False, server_default="pending"), sa.Column("rejection_reason", sa.Text()), sa.Column("admin_notes", sa.Text()), sa.Column("approved_by", sa.String(120)), sa.Column("approved_date", sa.DateTime()), sa.Column("registration_date", sa.DateTime(), nullable=False), sa.Column("last_login", sa.DateTime()), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("photo", sa.String(250)))
    op.create_index("ix_students_registration_no", "students", ["registration_no"]); op.create_index("ix_students_username", "students", ["username"]); op.create_index("ix_students_approval_status", "students", ["approval_status"])
    op.create_table("student_registration_answers", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False), sa.Column("question_id", sa.Integer(), sa.ForeignKey("custom_registration_questions.id"), nullable=False), sa.Column("value", sa.Text()), sa.UniqueConstraint("student_id", "question_id", name="uq_student_question_answer"))
    op.create_table("student_audit_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id")), sa.Column("action", sa.String(80), nullable=False), sa.Column("details", sa.Text()), sa.Column("actor", sa.String(120)), sa.Column("created_at", sa.DateTime(), nullable=False))


def downgrade():
    op.drop_table("student_audit_logs"); op.drop_table("student_registration_answers"); op.drop_index("ix_students_approval_status", table_name="students"); op.drop_index("ix_students_username", table_name="students"); op.drop_index("ix_students_registration_no", table_name="students"); op.drop_table("students"); op.drop_table("custom_registration_questions"); op.drop_table("registration_settings")
