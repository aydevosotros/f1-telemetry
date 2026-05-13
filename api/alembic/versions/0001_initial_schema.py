"""initial telemetry schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "capture_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("game_year", sa.Integer(), nullable=False, server_default="2025"),
        sa.Column("track_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_table(
        "drivers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("capture_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("car_index", sa.Integer(), nullable=False),
        sa.Column("driver_name", sa.String(length=120), nullable=True),
        sa.Column("team_name", sa.String(length=120), nullable=True),
        sa.UniqueConstraint("session_id", "car_index", name="uq_driver_session_car"),
    )
    op.create_table(
        "raw_packets",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("capture_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("packet_id", sa.Integer(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.LargeBinary(), nullable=False),
    )
    op.create_index("ix_raw_packets_session_received", "raw_packets", ["session_id", "received_at"])
    op.create_table(
        "telemetry_samples",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("capture_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("car_index", sa.Integer(), nullable=False),
        sa.Column("session_time", sa.Float(), nullable=False),
        sa.Column("speed_kph", sa.Integer(), nullable=True),
        sa.Column("throttle", sa.Float(), nullable=True),
        sa.Column("brake", sa.Float(), nullable=True),
        sa.Column("steer", sa.Float(), nullable=True),
        sa.Column("gear", sa.Integer(), nullable=True),
        sa.Column("engine_rpm", sa.Integer(), nullable=True),
        sa.Column("drs", sa.Boolean(), nullable=True),
        sa.Column("lap_number", sa.Integer(), nullable=True),
        sa.Column("lap_distance", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_telemetry_samples_session_car_time",
        "telemetry_samples",
        ["session_id", "car_index", "session_time"],
    )


def downgrade() -> None:
    op.drop_index("ix_telemetry_samples_session_car_time", table_name="telemetry_samples")
    op.drop_table("telemetry_samples")
    op.drop_index("ix_raw_packets_session_received", table_name="raw_packets")
    op.drop_table("raw_packets")
    op.drop_table("drivers")
    op.drop_table("capture_sessions")
