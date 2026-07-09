"""add event feature columns

Revision ID: 20260710_0002
Revises: 20260709_0001
Create Date: 2026-07-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "20260710_0002"
down_revision = "20260709_0001"
branch_labels = None
depends_on = None


EVENT_COLUMNS = {
    "registration_type": sa.Column(
        "registration_type",
        sa.String(length=30),
        nullable=False,
        server_default="teacher",
    ),
    "requires_photo": sa.Column(
        "requires_photo",
        sa.Boolean(),
        nullable=False,
        server_default=sa.true(),
    ),
    "collect_photo": sa.Column(
        "collect_photo",
        sa.Boolean(),
        nullable=False,
        server_default=sa.true(),
    ),
    "collect_email": sa.Column(
        "collect_email",
        sa.Boolean(),
        nullable=False,
        server_default=sa.true(),
    ),
    "collect_designation": sa.Column(
        "collect_designation",
        sa.Boolean(),
        nullable=False,
        server_default=sa.true(),
    ),
    "collect_subject": sa.Column(
        "collect_subject",
        sa.Boolean(),
        nullable=False,
        server_default=sa.true(),
    ),
    "collect_school_name": sa.Column(
        "collect_school_name",
        sa.Boolean(),
        nullable=False,
        server_default=sa.true(),
    ),
    "collect_school_area": sa.Column(
        "collect_school_area",
        sa.Boolean(),
        nullable=False,
        server_default=sa.true(),
    ),
    "collect_block": sa.Column(
        "collect_block",
        sa.Boolean(),
        nullable=False,
        server_default=sa.true(),
    ),
    "marquee_message": sa.Column(
        "marquee_message",
        sa.String(length=255),
        nullable=True,
    ),
    "payment_enabled": sa.Column(
        "payment_enabled",
        sa.Boolean(),
        nullable=False,
        server_default=sa.false(),
    ),
    "payment_amount": sa.Column(
        "payment_amount",
        sa.Float(),
        nullable=True,
        server_default="0",
    ),
    "payment_link": sa.Column(
        "payment_link",
        sa.String(length=500),
        nullable=True,
    ),
    "payment_notes": sa.Column(
        "payment_notes",
        sa.Text(),
        nullable=True,
    ),
    "whatsapp_ack_enabled": sa.Column(
        "whatsapp_ack_enabled",
        sa.Boolean(),
        nullable=False,
        server_default=sa.false(),
    ),
    "whatsapp_template": sa.Column(
        "whatsapp_template",
        sa.Text(),
        nullable=True,
    ),
    "whatsapp_group_enabled": sa.Column(
        "whatsapp_group_enabled",
        sa.Boolean(),
        nullable=False,
        server_default=sa.false(),
    ),
    "whatsapp_group_link": sa.Column(
        "whatsapp_group_link",
        sa.String(length=500),
        nullable=True,
    ),
    "acknowledgement_enabled": sa.Column(
        "acknowledgement_enabled",
        sa.Boolean(),
        nullable=False,
        server_default=sa.true(),
    ),
    "certificate_enabled": sa.Column(
        "certificate_enabled",
        sa.Boolean(),
        nullable=False,
        server_default=sa.true(),
    ),
    "attendance_enabled": sa.Column(
        "attendance_enabled",
        sa.Boolean(),
        nullable=False,
        server_default=sa.false(),
    ),
    "code_type": sa.Column(
        "code_type",
        sa.String(length=20),
        nullable=False,
        server_default="qr",
    ),
    "code_fields": sa.Column(
        "code_fields",
        sa.Text(),
        nullable=True,
    ),
    "reg_id_prefix": sa.Column(
        "reg_id_prefix",
        sa.String(length=20),
        nullable=True,
        server_default="EVT",
    ),
    "reg_id_next_number": sa.Column(
        "reg_id_next_number",
        sa.Integer(),
        nullable=False,
        server_default="1",
    ),
    "reg_id_padding": sa.Column(
        "reg_id_padding",
        sa.Integer(),
        nullable=False,
        server_default="4",
    ),
    "sponsor_brand": sa.Column(
        "sponsor_brand",
        sa.String(length=150),
        nullable=True,
    ),
    "sponsor_logo": sa.Column(
        "sponsor_logo",
        sa.String(length=250),
        nullable=True,
    ),
    "sponsor_image": sa.Column(
        "sponsor_image",
        sa.String(length=250),
        nullable=True,
    ),
    "sponsor_logo_position": sa.Column(
        "sponsor_logo_position",
        sa.String(length=20),
        nullable=True,
        server_default="left",
    ),
    "sponsor_logo_width": sa.Column(
        "sponsor_logo_width",
        sa.Integer(),
        nullable=True,
        server_default="160",
    ),
    "sponsor_logo_height": sa.Column(
        "sponsor_logo_height",
        sa.Integer(),
        nullable=True,
        server_default="90",
    ),
    "sponsor_banner_position": sa.Column(
        "sponsor_banner_position",
        sa.String(length=20),
        nullable=True,
        server_default="right",
    ),
    "sponsor_banner_width": sa.Column(
        "sponsor_banner_width",
        sa.Integer(),
        nullable=True,
        server_default="520",
    ),
    "sponsor_banner_height": sa.Column(
        "sponsor_banner_height",
        sa.Integer(),
        nullable=True,
        server_default="170",
    ),
    "sponsor_image_fit": sa.Column(
        "sponsor_image_fit",
        sa.String(length=20),
        nullable=True,
        server_default="contain",
    ),
    "qr_sharing_enabled": sa.Column(
        "qr_sharing_enabled",
        sa.Boolean(),
        nullable=False,
        server_default=sa.true(),
    ),
    "exam_enabled": sa.Column(
        "exam_enabled",
        sa.Boolean(),
        nullable=False,
        server_default=sa.false(),
    ),
    "is_active": sa.Column(
        "is_active",
        sa.Boolean(),
        nullable=False,
        server_default=sa.true(),
    ),
    "created_at": sa.Column(
        "created_at",
        sa.DateTime(),
        nullable=True,
    ),
}


def existing_column_names(table_name):
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade():
    existing_columns = existing_column_names("events")

    for name, column in EVENT_COLUMNS.items():
        if name not in existing_columns:
            op.add_column("events", column)


def downgrade():
    existing_columns = existing_column_names("events")

    for name in reversed(EVENT_COLUMNS):
        if name in existing_columns:
            op.drop_column("events", name)
