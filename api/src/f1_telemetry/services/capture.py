import asyncio
from dataclasses import replace
from uuid import UUID

from f1_telemetry.core.config import settings
from f1_telemetry.db.session import AsyncSessionLocal
from f1_telemetry.ingest.parser import DecodedGameSession, DecodedLapContext, F125PacketParser
from f1_telemetry.services.hub import hub
from f1_telemetry.services.sessions import session_service


class CaptureManager:
    def __init__(self) -> None:
        self._session_id: UUID | None = None
        self._transport: asyncio.DatagramTransport | None = None
        self._parser = F125PacketParser()
        self._lap_context: dict[int, DecodedLapContext] = {}
        self._game_session_context: DecodedGameSession | None = None
        self._lock = asyncio.Lock()

    @property
    def session_id(self) -> UUID | None:
        return self._session_id

    @property
    def recording(self) -> bool:
        return self._session_id is not None

    async def start(self, session_id: UUID) -> None:
        async with self._lock:
            if self._transport is not None:
                return
            loop = asyncio.get_running_loop()
            protocol = _TelemetryDatagramProtocol(self)
            transport, _ = await loop.create_datagram_endpoint(
                lambda: protocol,
                local_addr=(settings.udp_host, settings.udp_port),
            )
            self._session_id = session_id
            self._transport = transport

    async def stop(self) -> UUID | None:
        async with self._lock:
            session_id = self._session_id
            if self._transport is not None:
                self._transport.close()
            self._transport = None
            self._session_id = None
            self._lap_context.clear()
            self._game_session_context = None
            return session_id

    async def handle_payload(self, payload: bytes) -> None:
        session_id = self._session_id
        if session_id is None:
            return

        decoded = self._parser.decode(payload)
        if decoded.game_session is not None:
            self._game_session_context = decoded.game_session
        elif self._game_session_context is not None:
            decoded = replace(decoded, game_session=self._game_session_context)

        if decoded.laps:
            self._lap_context.update({lap.car_index: lap for lap in decoded.laps})

        if decoded.samples:
            decoded = replace(
                decoded,
                samples=tuple(
                    self._enrich_sample_with_lap_context(sample)
                    for sample in decoded.samples
                ),
            )

        async with AsyncSessionLocal() as db:
            samples = await session_service.persist_decoded_packet(
                db=db,
                session_id=session_id,
                payload=payload,
                decoded=decoded,
                store_raw=settings.store_raw_packets,
            )

        message = {
            "type": "telemetry",
            "session_id": str(session_id),
            "packet_id": decoded.packet_id,
            "sample_count": len(samples),
            "samples": [
                {
                    "car_index": sample.car_index,
                    "session_time": sample.session_time,
                    "speed_kph": sample.speed_kph,
                    "throttle": sample.throttle,
                    "brake": sample.brake,
                    "steer": sample.steer,
                    "gear": sample.gear,
                    "engine_rpm": sample.engine_rpm,
                    "drs": sample.drs,
                    "lap_number": sample.lap_number,
                    "lap_distance": sample.lap_distance,
                }
                for sample in samples
            ],
        }
        await hub.broadcast_live(message)
        await hub.broadcast_session(session_id, message)

    def _enrich_sample_with_lap_context(self, sample):
        lap = self._lap_context.get(
            sample.car_index,
            DecodedLapContext(sample.car_index, None, None),
        )
        return replace(
            sample,
            lap_number=sample.lap_number or lap.lap_number,
            lap_distance=(
                sample.lap_distance if sample.lap_distance is not None else lap.lap_distance
            ),
        )


class _TelemetryDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, manager: CaptureManager) -> None:
        self._manager = manager

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        asyncio.create_task(self._manager.handle_payload(data))


capture_manager = CaptureManager()
