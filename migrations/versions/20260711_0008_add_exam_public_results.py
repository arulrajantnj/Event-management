"""add administrator approval for public exam results

Revision ID: 20260711_0008
Revises: 20260711_0007
Create Date: 2026-07-11 01:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "20260711_0008"
down_revision = "20260711_0007"
branch_labels = None
depends_on = None


def upgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("online_exams")}
    if "public_results_published" not in columns:
        op.add_column(
            "online_exams",
            sa.Column("public_results_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("online_exams")}
    if "public_results_published" in columns:
        op.drop_column("online_exams", "public_results_published")
