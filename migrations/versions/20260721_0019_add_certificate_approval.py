"""add certificate preview approval

Revision ID: 20260721_0019
Revises: 20260720_0018
"""
from alembic import op
import sqlalchemy as sa


revision = "20260721_0019"
down_revision = "20260720_0018"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("participants", sa.Column("certificate_approved", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("participants", sa.Column("certificate_approved_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("participants", "certificate_approved_at")
    op.drop_column("participants", "certificate_approved")
