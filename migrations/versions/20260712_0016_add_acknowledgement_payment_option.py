"""add acknowledgement payment-details option

Revision ID: 20260712_0016
Revises: 20260712_0015
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa

revision = "20260712_0016"
down_revision = "20260712_0015"
branch_labels = None
depends_on = None


def upgrade():
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("events")}
    if "show_acknowledgement_payment_details" not in columns:
        op.add_column("events", sa.Column("show_acknowledgement_payment_details", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("events")}
    if "show_acknowledgement_payment_details" in columns:
        op.drop_column("events", "show_acknowledgement_payment_details")
