"""create homepage promotions

Revision ID: 20260712_0013
Revises: 20260711_0012
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa

revision = "20260712_0013"
down_revision = "20260711_0012"
branch_labels = None
depends_on = None

def upgrade():
    if "homepage_promotions" not in set(sa.inspect(op.get_bind()).get_table_names()):
        op.create_table("homepage_promotions", sa.Column("id", sa.Integer, primary_key=True), sa.Column("title", sa.String(180), nullable=False), sa.Column("message", sa.Text), sa.Column("image_filename", sa.String(250)), sa.Column("link_url", sa.String(500)), sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()), sa.Column("show_before_priority", sa.Boolean, nullable=False, server_default=sa.true()), sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"), sa.Column("layout", sa.String(20), nullable=False, server_default="banner"), sa.Column("image_fit", sa.String(20), nullable=False, server_default="cover"), sa.Column("accent_color", sa.String(20), nullable=False, server_default="#0d6efd"), sa.Column("created_at", sa.DateTime, nullable=False))

def downgrade():
    if "homepage_promotions" in set(sa.inspect(op.get_bind()).get_table_names()):
        op.drop_table("homepage_promotions")
