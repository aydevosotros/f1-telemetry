from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from f1_telemetry.db.base import Base


class CaptureSession(Base):
    __tablename__ = "capture_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160))
    game_year: Mapped[int] = mapped_column(default=2025)
    track_id: Mapped[int | None]
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), default="recording")
    notes: Mapped[str | None] = mapped_column(Text)

    drivers: Mapped[list["Driver"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    game_sessions: Mapped[list["GameSession"]] = relationship(
        back_populates="capture_session",
        cascade="all, delete-orphan",
    )
    samples: Mapped[list["TelemetrySample"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class GameSession(Base):
    __tablename__ = "game_sessions"
    __table_args__ = (
        UniqueConstraint("capture_session_id", "session_uid", name="uq_game_session_capture_uid"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    capture_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("capture_sessions.id", ondelete="CASCADE")
    )
    session_uid: Mapped[int]
    session_type: Mapped[int | None]
    track_id: Mapped[int | None]
    track_length: Mapped[int | None]
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    capture_session: Mapped[CaptureSession] = relationship(back_populates="game_sessions")


class Driver(Base):
    __tablename__ = "drivers"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "game_session_id",
            "car_index",
            name="uq_driver_session_game_car",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("capture_sessions.id", ondelete="CASCADE"))
    game_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="CASCADE")
    )
    car_index: Mapped[int]
    driver_name: Mapped[str | None] = mapped_column(String(120))
    team_name: Mapped[str | None] = mapped_column(String(120))

    session: Mapped[CaptureSession] = relationship(back_populates="drivers")


class RawPacket(Base):
    __tablename__ = "raw_packets"
    __table_args__ = (Index("ix_raw_packets_session_received", "session_id", "received_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("capture_sessions.id", ondelete="CASCADE"))
    game_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="SET NULL")
    )
    packet_id: Mapped[int | None]
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    payload: Mapped[bytes] = mapped_column(LargeBinary)


class TelemetrySample(Base):
    __tablename__ = "telemetry_samples"
    __table_args__ = (
        Index("ix_telemetry_samples_session_car_time", "session_id", "car_index", "session_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("capture_sessions.id", ondelete="CASCADE"))
    game_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="SET NULL")
    )
    car_index: Mapped[int]
    session_time: Mapped[float] = mapped_column(Float)
    speed_kph: Mapped[int | None]
    throttle: Mapped[float | None] = mapped_column(Float)
    brake: Mapped[float | None] = mapped_column(Float)
    steer: Mapped[float | None] = mapped_column(Float)
    gear: Mapped[int | None]
    engine_rpm: Mapped[int | None]
    drs: Mapped[bool | None]
    lap_number: Mapped[int | None]
    lap_distance: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    session: Mapped[CaptureSession] = relationship(back_populates="samples")
