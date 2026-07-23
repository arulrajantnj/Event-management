"""add event text color and size options

Revision ID: 20260723_0021
Revises: 20260723_0020
"""
from alembic import op
import sqlalchemy as sa


revision = "20260723_0021"
down_revision = "20260723_0020"
branch_labels = None
depends_on = None


def upgrade():
    for column_name, default in (
        ("title_font_color", "#ffffff"),
        ("description_font_color", "#6c757d"),
        ("marquee_font_color", "#ffffff"),
        ("registration_font_color", "#0d6efd"),
    ):
        op.add_column("events", sa.Column(column_name, sa.String(length=7), nullable=False, server_default=default))
    for column_name in (
        "title_font_size",
        "description_font_size",
        "marquee_font_size",
        "registration_font_size",
    ):
        op.add_column("events", sa.Column(column_name, sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    for column_name in (
        "registration_font_size",
        "marquee_font_size",
        "description_font_size",
        "title_font_size",
        "registration_font_color",
        "marquee_font_color",
        "description_font_color",
        "title_font_color",
    ):
        op.drop_column("events", column_name)
