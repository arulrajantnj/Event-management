"""store school details returned from UDISE

Revision ID: 20260803_0025
Revises: 20260802_0024
"""
from alembic import op
import sqlalchemy as sa


revision = "20260803_0025"
down_revision = "20260802_0024"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("students", sa.Column("school_block", sa.String(120)))
    op.add_column("students", sa.Column("school_management", sa.String(160)))
    op.add_column("students", sa.Column("school_details", sa.Text()))


def downgrade():
    op.drop_column("students", "school_details")
    op.drop_column("students", "school_management")
    op.drop_column("students", "school_block")
