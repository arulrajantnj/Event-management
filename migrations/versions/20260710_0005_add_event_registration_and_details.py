"""add participant entry and event detail settings

Revision ID: 20260710_0005
Revises: 20260710_0004
Create Date: 2026-07-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "20260710_0005"
down_revision = "20260710_0004"
branch_labels = None
depends_on = None


COLUMNS = {
    "public_registration_enabled": sa.Column("public_registration_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    "participant_bulk_upload_enabled": sa.Column("participant_bulk_upload_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    "show_venue": sa.Column("show_venue", sa.Boolean(), nullable=False, server_default=sa.false()),
    "venue": sa.Column("venue", sa.String(length=255), nullable=True),
    "show_event_date": sa.Column("show_event_date", sa.Boolean(), nullable=False, server_default=sa.false()),
    "event_date": sa.Column("event_date", sa.Date(), nullable=True),
    "show_event_time": sa.Column("show_event_time", sa.Boolean(), nullable=False, server_default=sa.false()),
    "event_time": sa.Column("event_time", sa.String(length=100), nullable=True),
    "show_chief_guest": sa.Column("show_chief_guest", sa.Boolean(), nullable=False, server_default=sa.false()),
    "chief_guest": sa.Column("chief_guest", sa.String(length=255), nullable=True),
}


def column_names():
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("events")}


def upgrade():
    existing = column_names()
    for name, column in COLUMNS.items():
        if name not in existing:
            op.add_column("events", column)


def downgrade():
    existing = column_names()
    for name in reversed(COLUMNS):
        if name in existing:
            op.drop_column("events", name)
