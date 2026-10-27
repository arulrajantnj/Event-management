"""add webinar meeting control plane tables

Revision ID: 20261026_0028
Revises: 20260803_0025
"""
from alembic import op
import sqlalchemy as sa

revision = "20261026_0028"
down_revision = "20260803_0025"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    event_columns = {column["name"] for column in sa.inspect(bind).get_columns("events")}
    if "live_meeting_enabled" not in event_columns:
        op.add_column("events", sa.Column("live_meeting_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "live_meetings" not in tables:
        op.create_table(
            "live_meetings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False, unique=True),
            sa.Column("room_name", sa.String(120), nullable=False, unique=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="scheduled"),
            sa.Column("viewer_count_estimate", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("started_at", sa.DateTime()),
            sa.Column("ended_at", sa.DateTime()),
        )
    if "live_meeting_speakers" not in tables:
        op.create_table(
            "live_meeting_speakers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("meeting_id", sa.Integer(), sa.ForeignKey("live_meetings.id", ondelete="CASCADE"), nullable=False),
            sa.Column("participant_id", sa.Integer(), sa.ForeignKey("participants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("invited_by", sa.String(100), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="invited"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("meeting_id", "participant_id", name="uq_meeting_speaker"),
        )
        op.create_index("ix_live_meeting_speakers_meeting_id", "live_meeting_speakers", ["meeting_id"])
        op.create_index("ix_live_meeting_speakers_participant_id", "live_meeting_speakers", ["participant_id"])
    if "live_meeting_interactions" not in tables:
        op.create_table(
            "live_meeting_interactions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("meeting_id", sa.Integer(), sa.ForeignKey("live_meetings.id", ondelete="CASCADE"), nullable=False),
            sa.Column("participant_id", sa.Integer(), sa.ForeignKey("participants.id", ondelete="SET NULL")),
            sa.Column("kind", sa.String(20), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(20), nullable=False, server_default="open"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_live_meeting_interactions_meeting_id", "live_meeting_interactions", ["meeting_id"])
        op.create_index("ix_live_meeting_interactions_participant_id", "live_meeting_interactions", ["participant_id"])
        op.create_index("ix_live_meeting_interactions_created_at", "live_meeting_interactions", ["created_at"])


def downgrade():
    op.drop_table("live_meeting_interactions")
    op.drop_table("live_meeting_speakers")
    op.drop_table("live_meetings")
    op.drop_column("events", "live_meeting_enabled")
