"""add chess staff, certificates, notifications and API token storage

Revision ID: 20260711_0012
Revises: 20260711_0011
"""
from alembic import op
import sqlalchemy as sa

revision = "20260711_0012"
down_revision = "20260711_0011"
branch_labels = None
depends_on = None

def upgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "chess_staff" not in tables:
        op.create_table("chess_staff",sa.Column("id",sa.Integer,primary_key=True),sa.Column("name",sa.String(150),nullable=False),sa.Column("username",sa.String(80),nullable=False),sa.Column("password_hash",sa.String(255),nullable=False),sa.Column("role",sa.String(30),nullable=False,server_default="tournament_admin"),sa.Column("is_active",sa.Boolean,nullable=False,server_default=sa.true()),sa.Column("created_at",sa.DateTime,nullable=False),sa.UniqueConstraint("username",name="uq_chess_staff_username"))
    if "chess_staff_assignments" not in tables:
        op.create_table("chess_staff_assignments",sa.Column("id",sa.Integer,primary_key=True),sa.Column("staff_id",sa.Integer,sa.ForeignKey("chess_staff.id"),nullable=False),sa.Column("tournament_id",sa.Integer,sa.ForeignKey("chess_tournaments.id"),nullable=False),sa.Column("age_group_id",sa.Integer,sa.ForeignKey("chess_age_groups.id")),sa.UniqueConstraint("staff_id","tournament_id","age_group_id",name="uq_chess_staff_assignment")); op.create_index("ix_chess_staff_assignment_staff","chess_staff_assignments",["staff_id"])
    if "chess_certificates" not in tables:
        op.create_table("chess_certificates",sa.Column("id",sa.Integer,primary_key=True),sa.Column("participant_id",sa.Integer,sa.ForeignKey("chess_participants.id"),nullable=False),sa.Column("certificate_number",sa.String(64),nullable=False),sa.Column("certificate_type",sa.String(40),nullable=False,server_default="participation"),sa.Column("file_path",sa.String(250)),sa.Column("issued_at",sa.DateTime,nullable=False),sa.UniqueConstraint("certificate_number",name="uq_chess_certificate_number")); op.create_index("ix_chess_certificates_player","chess_certificates",["participant_id"])
    if "chess_notifications" not in tables:
        op.create_table("chess_notifications",sa.Column("id",sa.Integer,primary_key=True),sa.Column("tournament_id",sa.Integer,sa.ForeignKey("chess_tournaments.id"),nullable=False),sa.Column("age_group_id",sa.Integer,sa.ForeignKey("chess_age_groups.id")),sa.Column("title",sa.String(200),nullable=False),sa.Column("body",sa.Text,nullable=False),sa.Column("category",sa.String(40),nullable=False,server_default="announcement"),sa.Column("created_at",sa.DateTime,nullable=False)); op.create_index("ix_chess_notifications_tournament","chess_notifications",["tournament_id","created_at"])
    if "chess_api_tokens" not in tables:
        op.create_table("chess_api_tokens",sa.Column("id",sa.Integer,primary_key=True),sa.Column("tournament_id",sa.Integer,sa.ForeignKey("chess_tournaments.id"),nullable=False),sa.Column("label",sa.String(120),nullable=False),sa.Column("token_hash",sa.String(128),nullable=False),sa.Column("is_active",sa.Boolean,nullable=False,server_default=sa.true()),sa.Column("created_at",sa.DateTime,nullable=False),sa.UniqueConstraint("token_hash",name="uq_chess_api_token_hash")); op.create_index("ix_chess_api_tokens_tournament","chess_api_tokens",["tournament_id"])

def downgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    for name in ("chess_api_tokens","chess_notifications","chess_certificates","chess_staff_assignments","chess_staff"):
        if name in tables: op.drop_table(name)
