"""add registration display controls and whatsapp details

Revision ID: 20260711_0010
Revises: 20260711_0009
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa

revision = "20260711_0010"
down_revision = "20260711_0009"
branch_labels = None
depends_on = None


def upgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("events")}
    additions = [
        ("show_registration_header", sa.Boolean(), sa.true()),
        ("show_registration_instructions", sa.Boolean(), sa.true()),
        ("show_registration_sponsor", sa.Boolean(), sa.false()),
        ("whatsapp_ack_fields", sa.Text(), None),
    ]
    for name, column_type, default in additions:
        if name not in columns:
            kwargs = {"nullable": False} if default is not None else {"nullable": True}
            if default is not None:
                kwargs["server_default"] = default
            op.add_column("events", sa.Column(name, column_type, **kwargs))


def downgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("events")}
    for name in ("whatsapp_ack_fields", "show_registration_sponsor", "show_registration_instructions", "show_registration_header"):
        if name in columns:
            op.drop_column("events", name)
