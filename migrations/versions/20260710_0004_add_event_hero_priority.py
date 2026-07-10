"""add event hero priority

Revision ID: 20260710_0004
Revises: 20260710_0003
Create Date: 2026-07-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "20260710_0004"
down_revision = "20260710_0003"
branch_labels = None
depends_on = None


def existing_column_names(table_name):
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade():
    if "hero_priority" not in existing_column_names("events"):
        op.add_column(
            "events",
            sa.Column(
                "hero_priority",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade():
    if "hero_priority" in existing_column_names("events"):
        op.drop_column("events", "hero_priority")
