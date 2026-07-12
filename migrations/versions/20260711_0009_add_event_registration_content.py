"""add event registration page content

Revision ID: 20260711_0009
Revises: 20260711_0008
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa


revision = "20260711_0009"
down_revision = "20260711_0008"
branch_labels = None
depends_on = None


def upgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("events")}
    if "registration_header" not in columns:
        op.add_column("events", sa.Column("registration_header", sa.String(length=255), nullable=True))
    if "registration_instructions" not in columns:
        op.add_column("events", sa.Column("registration_instructions", sa.Text(), nullable=True))


def downgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("events")}
    if "registration_instructions" in columns:
        op.drop_column("events", "registration_instructions")
    if "registration_header" in columns:
        op.drop_column("events", "registration_header")
