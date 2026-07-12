"""add acknowledgement instructions and thank-you message

Revision ID: 20260712_0015
Revises: 20260712_0014
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa

revision = "20260712_0015"
down_revision = "20260712_0014"
branch_labels = None
depends_on = None


def upgrade():
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("events")}
    additions = [
        ("acknowledgement_instructions", sa.Text(), None),
        ("show_acknowledgement_instructions", sa.Boolean(), sa.false()),
        ("acknowledgement_thank_you", sa.String(500), None),
        ("show_acknowledgement_thank_you", sa.Boolean(), sa.false()),
    ]
    for name, column_type, default in additions:
        if name not in columns:
            kwargs = {"nullable": False, "server_default": default} if default is not None else {"nullable": True}
            op.add_column("events", sa.Column(name, column_type, **kwargs))


def downgrade():
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("events")}
    for name in ("show_acknowledgement_thank_you", "acknowledgement_thank_you", "show_acknowledgement_instructions", "acknowledgement_instructions"):
        if name in columns:
            op.drop_column("events", name)
