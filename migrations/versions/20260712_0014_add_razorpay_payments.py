"""add Razorpay payment tracking

Revision ID: 20260712_0014
Revises: 20260712_0013
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa

revision = "20260712_0014"
down_revision = "20260712_0013"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    event_columns = {item["name"] for item in sa.inspect(bind).get_columns("events")}
    participant_columns = {item["name"] for item in sa.inspect(bind).get_columns("participants")}
    if "payment_gateway" not in event_columns:
        op.add_column("events", sa.Column("payment_gateway", sa.String(30), nullable=False, server_default="manual"))
    if "payment_status" not in participant_columns:
        op.add_column("participants", sa.Column("payment_status", sa.String(30), nullable=False, server_default="not_required"))
    if "razorpay_order_id" not in participant_columns:
        op.add_column("participants", sa.Column("razorpay_order_id", sa.String(100)))
    if "razorpay_payment_id" not in participant_columns:
        op.add_column("participants", sa.Column("razorpay_payment_id", sa.String(100)))
    if "payment_verified_at" not in participant_columns:
        op.add_column("participants", sa.Column("payment_verified_at", sa.DateTime))


def downgrade():
    bind = op.get_bind()
    event_columns = {item["name"] for item in sa.inspect(bind).get_columns("events")}
    participant_columns = {item["name"] for item in sa.inspect(bind).get_columns("participants")}
    for name in ("payment_verified_at", "razorpay_payment_id", "razorpay_order_id", "payment_status"):
        if name in participant_columns:
            op.drop_column("participants", name)
    if "payment_gateway" in event_columns:
        op.drop_column("events", "payment_gateway")
