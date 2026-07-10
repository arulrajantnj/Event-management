"""create missing feature tables

Revision ID: 20260710_0003
Revises: 20260710_0002
Create Date: 2026-07-10 00:00:00.000000

"""
from alembic import op

from models import db


revision = "20260710_0003"
down_revision = "20260710_0002"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    db.metadata.create_all(bind=bind)


def downgrade():
    pass
