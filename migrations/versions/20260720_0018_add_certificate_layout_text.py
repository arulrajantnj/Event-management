"""add custom text to certificate layouts

Revision ID: 20260720_0018
Revises: 20260720_0017
Create Date: 2026-07-20 20:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "20260720_0018"
down_revision = "20260720_0017"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("certificate_layout", sa.Column("text_content", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("certificate_layout", "text_content")
