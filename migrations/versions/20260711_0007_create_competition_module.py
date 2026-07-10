"""create children's competition module

Revision ID: 20260711_0007
Revises: 20260710_0006
Create Date: 2026-07-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "20260711_0007"
down_revision = "20260710_0006"
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "competitions" not in existing:
        op.create_table(
            "competitions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
            sa.Column("name", sa.String(length=180), nullable=False),
            sa.Column("category", sa.String(length=100)),
            sa.Column("description", sa.Text()),
            sa.Column("registration_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("results_published", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime()),
        )
    if "competition_registrations" not in existing:
        op.create_table(
            "competition_registrations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id"), nullable=False),
            sa.Column("registration_no", sa.String(length=32), nullable=False, unique=True),
            sa.Column("participant_name", sa.String(length=150), nullable=False),
            sa.Column("gender", sa.String(length=20), nullable=False, server_default="Not specified"),
            sa.Column("age", sa.Integer()),
            sa.Column("mobile", sa.String(length=20)),
            sa.Column("school_name", sa.String(length=220)),
            sa.Column("class_name", sa.String(length=60)),
            sa.Column("is_present", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("score", sa.Float()),
            sa.Column("rank", sa.String(length=40), nullable=False, server_default="Participant Certificate"),
            sa.Column("judge_submitted_at", sa.DateTime()),
            sa.Column("created_at", sa.DateTime()),
            sa.UniqueConstraint("competition_id", "mobile", "participant_name", name="uq_competition_registration"),
        )
    if "competition_judges" not in existing:
        op.create_table(
            "competition_judges",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id"), nullable=False),
            sa.Column("name", sa.String(length=150), nullable=False),
            sa.Column("username", sa.String(length=80), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime()),
            sa.UniqueConstraint("username", name="uq_competition_judge_username"),
        )


def downgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    for table in ("competition_judges", "competition_registrations", "competitions"):
        if table in existing:
            op.drop_table(table)
