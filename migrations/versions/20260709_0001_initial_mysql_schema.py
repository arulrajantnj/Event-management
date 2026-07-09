"""initial mysql schema

Revision ID: 20260709_0001
Revises:
Create Date: 2026-07-09 00:00:00.000000

"""
from alembic import op

from models import db


revision = "20260709_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    db.metadata.create_all(bind=bind)


def downgrade():
    bind = op.get_bind()
    db.metadata.drop_all(bind=bind)
