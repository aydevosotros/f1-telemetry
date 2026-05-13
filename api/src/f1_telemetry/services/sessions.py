from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from f1_telemetry.ingest.parser import DecodedPacket
from f1_telemetry.models.entities import (
    CaptureSession,
    Driver,
    GameSession,
    RawPacket,
    TelemetrySample,
)


class SessionService:
    async def create_session(
        self,
        db: AsyncSession,
        name: str | None,
        notes: str | None,
    ) -> CaptureSession:
        session = CaptureSession(
            name=name or f"F1 25 capture {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}",
            notes=notes,
            status="recording",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def finish_session(self, db: AsyncSession, session_id: UUID) -> CaptureSession | None:
        session = await db.get(CaptureSession, session_id)
        if session is None:
            return None
        session.status = "recorded"
        session.ended_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(session)
        return session

    async def list_sessions(self, db: AsyncSession) -> list[CaptureSession]:
        result = await db.execute(select(CaptureSession).order_by(CaptureSession.started_at.desc()))
        return list(result.scalars().all())

    async def get_session(self, db: AsyncSession, session_id: UUID) -> CaptureSession | None:
        result = await db.execute(
            select(CaptureSession)
            .where(CaptureSession.id == session_id)
            .options(selectinload(CaptureSession.drivers))
        )
        return result.scalar_one_or_none()

    async def list_game_sessions(
        self,
        db: AsyncSession,
        capture_session_id: UUID,
    ) -> list[GameSession]:
        result = await db.execute(
            select(GameSession)
            .where(GameSession.capture_session_id == capture_session_id)
            .order_by(GameSession.started_at.asc())
        )
        return list(result.scalars().all())

    async def list_samples(
        self,
        db: AsyncSession,
        session_id: UUID,
        game_session_id: UUID | None,
        car_index: int | None,
        lap_number: int | None,
        limit: int,
    ) -> list[TelemetrySample]:
        stmt = (
            select(TelemetrySample)
            .where(TelemetrySample.session_id == session_id)
            .order_by(TelemetrySample.session_time.asc())
            .limit(limit)
        )
        if game_session_id is not None:
            stmt = stmt.where(TelemetrySample.game_session_id == game_session_id)
        if car_index is not None:
            stmt = stmt.where(TelemetrySample.car_index == car_index)
        if lap_number is not None:
            stmt = stmt.where(TelemetrySample.lap_number == lap_number)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list_laps(
        self,
        db: AsyncSession,
        session_id: UUID,
        game_session_id: UUID | None,
        car_index: int | None,
    ) -> list[dict]:
        stmt = (
            select(
                TelemetrySample.game_session_id,
                TelemetrySample.car_index,
                TelemetrySample.lap_number,
                func.count(TelemetrySample.id).label("sample_count"),
                func.min(TelemetrySample.session_time).label("start_session_time"),
                func.max(TelemetrySample.session_time).label("end_session_time"),
                func.min(TelemetrySample.lap_distance).label("min_lap_distance"),
                func.max(TelemetrySample.lap_distance).label("max_lap_distance"),
            )
            .where(
                TelemetrySample.session_id == session_id,
                TelemetrySample.lap_number.is_not(None),
            )
            .group_by(
                TelemetrySample.game_session_id,
                TelemetrySample.car_index,
                TelemetrySample.lap_number,
            )
            .order_by(TelemetrySample.car_index.asc(), TelemetrySample.lap_number.asc())
        )
        if game_session_id is not None:
            stmt = stmt.where(TelemetrySample.game_session_id == game_session_id)
        if car_index is not None:
            stmt = stmt.where(TelemetrySample.car_index == car_index)

        rows = (await db.execute(stmt)).mappings().all()
        return [
            {
                "game_session_id": row["game_session_id"],
                "car_index": row["car_index"],
                "lap_number": row["lap_number"],
                "sample_count": row["sample_count"],
                "start_session_time": row["start_session_time"],
                "end_session_time": row["end_session_time"],
                "lap_time": row["end_session_time"] - row["start_session_time"],
                "min_lap_distance": row["min_lap_distance"],
                "max_lap_distance": row["max_lap_distance"],
            }
            for row in rows
        ]

    async def persist_decoded_packet(
        self,
        db: AsyncSession,
        session_id: UUID,
        payload: bytes,
        decoded: DecodedPacket,
        store_raw: bool,
    ) -> list[TelemetrySample]:
        game_session = await self._upsert_game_session(db, session_id, decoded)
        game_session_id = game_session.id if game_session is not None else None

        if store_raw:
            db.add(
                RawPacket(
                    session_id=session_id,
                    game_session_id=game_session_id,
                    packet_id=decoded.packet_id,
                    received_at=decoded.received_at,
                    payload=payload,
                )
            )

        if decoded.drivers:
            for driver in decoded.drivers:
                team_name = None if driver.team_id is None else f"Team {driver.team_id}"
                stmt = (
                    insert(Driver)
                    .values(
                        session_id=session_id,
                        game_session_id=game_session_id,
                        car_index=driver.car_index,
                        driver_name=driver.driver_name,
                        team_name=team_name,
                    )
                    .on_conflict_do_update(
                        constraint="uq_driver_session_game_car",
                        set_={
                            "driver_name": driver.driver_name,
                            "team_name": team_name,
                        },
                    )
                )
                await db.execute(stmt)

        rows = [
            TelemetrySample(
                session_id=session_id,
                game_session_id=game_session_id,
                car_index=sample.car_index,
                session_time=sample.session_time,
                speed_kph=sample.speed_kph,
                throttle=sample.throttle,
                brake=sample.brake,
                steer=sample.steer,
                gear=sample.gear,
                engine_rpm=sample.engine_rpm,
                drs=sample.drs,
                lap_number=sample.lap_number,
                lap_distance=sample.lap_distance,
            )
            for sample in decoded.samples
        ]
        db.add_all(rows)
        await db.commit()
        return rows

    async def _upsert_game_session(
        self,
        db: AsyncSession,
        capture_session_id: UUID,
        decoded: DecodedPacket,
    ) -> GameSession | None:
        if decoded.game_session is None:
            return None

        stmt = (
            insert(GameSession)
            .values(
                capture_session_id=capture_session_id,
                session_uid=decoded.game_session.session_uid,
                session_type=decoded.game_session.session_type,
                track_id=decoded.game_session.track_id,
                track_length=decoded.game_session.track_length,
                started_at=decoded.received_at,
                last_seen_at=decoded.received_at,
            )
            .on_conflict_do_update(
                constraint="uq_game_session_capture_uid",
                set_={
                    "session_type": decoded.game_session.session_type,
                    "track_id": decoded.game_session.track_id,
                    "track_length": decoded.game_session.track_length,
                    "last_seen_at": decoded.received_at,
                },
            )
            .returning(GameSession)
        )
        result = await db.execute(stmt)
        return result.scalar_one()


session_service = SessionService()
