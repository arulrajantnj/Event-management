"""add per-event public font choices

Revision ID: 20260723_0020
Revises: 20260721_0019
"""
from alembic import op
import sqlalchemy as sa


revision = "20260723_0020"
down_revision = "20260721_0019"
branch_labels = None
depends_on = None


def upgrade():
    for column_name in (
        "title_font_family",
        "description_font_family",
        "marquee_font_family",
        "registration_font_family",
    ):
        op.add_column("events", sa.Column(column_name, sa.String(length=120), nullable=False, server_default="Poppins"))


def downgrade():
    for column_name in (
        "registration_font_family",
        "marquee_font_family",
        "description_font_family",
        "title_font_family",
    ):
        op.drop_column("events", column_name)
