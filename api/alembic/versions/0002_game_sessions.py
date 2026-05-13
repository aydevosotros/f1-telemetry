"""add game session segmentation

Revision ID: 0002_game_sessions
Revises: 0001_initial_schema
Create Date: 2026-05-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_game_sessions"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "game_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "capture_session_id",
            sa.Uuid(),
            sa.ForeignKey("capture_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_uid", sa.BigInteger(), nullable=False),
        sa.Column("session_type", sa.Integer(), nullable=True),
        sa.Column("track_id", sa.Integer(), nullable=True),
        sa.Column("track_length", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "capture_session_id",
            "session_uid",
            name="uq_game_session_capture_uid",
        ),
    )
    op.add_column("drivers", sa.Column("game_session_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_drivers_game_session_id_game_sessions",
        "drivers",
        "game_sessions",
        ["game_session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("uq_driver_session_car", "drivers", type_="unique")
    op.create_unique_constraint(
        "uq_driver_session_game_car",
        "drivers",
        ["session_id", "game_session_id", "car_index"],
    )
    op.add_column("raw_packets", sa.Column("game_session_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_raw_packets_game_session_id_game_sessions",
        "raw_packets",
        "game_sessions",
        ["game_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("telemetry_samples", sa.Column("game_session_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_telemetry_samples_game_session_id_game_sessions",
        "telemetry_samples",
        "game_sessions",
        ["game_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_telemetry_samples_game_car_lap_time",
        "telemetry_samples",
        ["game_session_id", "car_index", "lap_number", "session_time"],
    )


def downgrade() -> None:
    op.drop_index("ix_telemetry_samples_game_car_lap_time", table_name="telemetry_samples")
    op.drop_constraint(
        "fk_telemetry_samples_game_session_id_game_sessions",
        "telemetry_samples",
        type_="foreignkey",
    )
    op.drop_column("telemetry_samples", "game_session_id")
    op.drop_constraint(
        "fk_raw_packets_game_session_id_game_sessions",
        "raw_packets",
        type_="foreignkey",
    )
    op.drop_column("raw_packets", "game_session_id")
    op.drop_constraint("uq_driver_session_game_car", "drivers", type_="unique")
    op.create_unique_constraint("uq_driver_session_car", "drivers", ["session_id", "car_index"])
    op.drop_constraint("fk_drivers_game_session_id_game_sessions", "drivers", type_="foreignkey")
    op.drop_column("drivers", "game_session_id")
    op.drop_table("game_sessions")
