from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import import_module
from struct import unpack_from
from typing import Any


@dataclass(frozen=True)
class DecodedSample:
    car_index: int
    session_time: float
    speed_kph: int | None = None
    throttle: float | None = None
    brake: float | None = None
    steer: float | None = None
    gear: int | None = None
    engine_rpm: int | None = None
    drs: bool | None = None
    lap_number: int | None = None
    lap_distance: float | None = None


@dataclass(frozen=True)
class DecodedLapContext:
    car_index: int
    lap_number: int | None
    lap_distance: float | None


@dataclass(frozen=True)
class DecodedDriver:
    car_index: int
    driver_name: str | None
    team_id: int | None = None


@dataclass(frozen=True)
class DecodedGameSession:
    session_uid: int
    session_type: int | None = None
    track_id: int | None = None
    track_length: int | None = None


@dataclass(frozen=True)
class DecodedPacket:
    packet_id: int | None
    received_at: datetime
    game_session: DecodedGameSession | None = None
    samples: tuple[DecodedSample, ...] = ()
    laps: tuple[DecodedLapContext, ...] = ()
    drivers: tuple[DecodedDriver, ...] = ()


class F125PacketParser:
    """Adapter boundary for F1 25 UDP packets.

    The app stores normalized samples independently from the parser dependency.
    The fallback header reader keeps raw capture useful even if detailed packet
    decoding needs to be adjusted against real packet fixtures.
    """

    def __init__(self) -> None:
        self._packets_module = self._load_packets_module()

    def decode(self, payload: bytes, received_at: datetime | None = None) -> DecodedPacket:
        received = received_at or datetime.now(UTC)
        packet_id = self.packet_id(payload)
        packet = self._resolve_packet(payload)
        samples = self._samples_from_packet(packet) if packet is not None else []
        laps = self._laps_from_packet(packet) if packet is not None else []
        drivers = self._drivers_from_packet(packet) if packet is not None else []
        game_session = self._game_session_from_packet(packet) if packet is not None else None
        return DecodedPacket(
            packet_id=packet_id,
            received_at=received,
            game_session=game_session,
            samples=tuple(samples),
            laps=tuple(laps),
            drivers=tuple(drivers),
        )

    def packet_id(self, payload: bytes) -> int | None:
        if len(payload) < 7:
            return None

        # F1 25 packet headers are little-endian and begin with packet format.
        packet_format = unpack_from("<H", payload, 0)[0]
        if packet_format != 2025:
            return None

        # Packet ID offset is stable in the modern Codemasters packet header.
        return payload[6]

    def _load_packets_module(self) -> Any | None:
        for module_name in ("f1.packets", "f1_packets", "f1_2025_telemetry"):
            try:
                return import_module(module_name)
            except ModuleNotFoundError:
                continue
        return None

    def _resolve_packet(self, payload: bytes) -> Any | None:
        if self._packets_module is None:
            return None

        decode_candidates = ("resolve", "unpack_udp_packet", "parse_udp_packet", "decode_packet")
        for name in decode_candidates:
            decoder = getattr(self._packets_module, name, None)
            if decoder is None:
                continue
            try:
                return decoder(payload)
            except Exception:
                continue
        return None

    def _samples_from_packet(self, packet: Any) -> list[DecodedSample]:
        header = getattr(packet, "header", None)
        session_time = float(
            getattr(header, "session_time", 0.0) or getattr(header, "m_sessionTime", 0.0) or 0.0
        )
        car_telemetry = (
            getattr(packet, "car_telemetry_data", None)
            or getattr(packet, "m_carTelemetryData", None)
            or getattr(packet, "carTelemetryData", None)
        )
        if not car_telemetry:
            return []

        samples: list[DecodedSample] = []
        for car_index, car in enumerate(car_telemetry):
            lap = self._first_attr(car, "current_lap_num", "currentLapNum", "m_currentLapNum")
            samples.append(
                DecodedSample(
                    car_index=car_index,
                    session_time=session_time,
                    speed_kph=self._int_attr(car, "speed", "m_speed"),
                    throttle=self._float_attr(car, "throttle", "m_throttle"),
                    brake=self._float_attr(car, "brake", "m_brake"),
                    steer=self._float_attr(car, "steer", "m_steer"),
                    gear=self._int_attr(car, "gear", "m_gear"),
                    engine_rpm=self._int_attr(car, "engine_rpm", "m_engineRPM"),
                    drs=self._bool_attr(car, "drs", "m_drs"),
                    lap_number=None if lap is None else int(lap),
                    lap_distance=self._float_attr(
                        car,
                        "lap_distance",
                        "lapDistance",
                        "m_lapDistance",
                    ),
                )
            )
        return samples

    def _laps_from_packet(self, packet: Any) -> list[DecodedLapContext]:
        lap_data = (
            getattr(packet, "lap_data", None)
            or getattr(packet, "m_lapData", None)
            or getattr(packet, "lapData", None)
        )
        if not lap_data:
            return []

        laps: list[DecodedLapContext] = []
        for car_index, lap in enumerate(lap_data):
            lap_number = self._int_attr(lap, "current_lap_num", "currentLapNum", "m_currentLapNum")
            laps.append(
                DecodedLapContext(
                    car_index=car_index,
                    lap_number=lap_number,
                    lap_distance=self._float_attr(
                        lap,
                        "lap_distance",
                        "lapDistance",
                        "m_lapDistance",
                    ),
                )
            )
        return laps

    def _drivers_from_packet(self, packet: Any) -> list[DecodedDriver]:
        participants = (
            getattr(packet, "participants", None)
            or getattr(packet, "m_participants", None)
            or getattr(packet, "participant_data", None)
        )
        if not participants:
            return []

        active_count = self._int_attr(packet, "num_active_cars", "m_numActiveCars")
        drivers: list[DecodedDriver] = []
        for car_index, participant in enumerate(participants):
            if active_count is not None and car_index >= active_count:
                break
            drivers.append(
                DecodedDriver(
                    car_index=car_index,
                    driver_name=self._string_attr(participant, "name", "m_name"),
                    team_id=self._int_attr(participant, "team_id", "m_teamId"),
                )
            )
        return drivers

    def _game_session_from_packet(self, packet: Any) -> DecodedGameSession | None:
        header = getattr(packet, "header", None)
        session_uid = self._int_attr(header, "session_uid", "m_sessionUID")
        if session_uid is None:
            return None

        return DecodedGameSession(
            session_uid=session_uid,
            session_type=self._int_attr(packet, "session_type", "m_sessionType"),
            track_id=self._int_attr(packet, "track_id", "m_trackId"),
            track_length=self._int_attr(packet, "track_length", "m_trackLength"),
        )

    def _int_attr(self, obj: Any, *names: str) -> int | None:
        value = self._first_attr(obj, *names)
        return None if value is None else int(value)

    def _float_attr(self, obj: Any, *names: str) -> float | None:
        value = self._first_attr(obj, *names)
        return None if value is None else float(value)

    def _bool_attr(self, obj: Any, *names: str) -> bool | None:
        value = self._first_attr(obj, *names)
        return None if value is None else bool(value)

    def _string_attr(self, obj: Any, *names: str) -> str | None:
        value = self._first_attr(obj, *names)
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.split(b"\x00", 1)[0].decode(errors="ignore") or None
        return str(value).strip() or None

    def _first_attr(self, obj: Any, *names: str) -> Any | None:
        for name in names:
            if hasattr(obj, name):
                return getattr(obj, name)
        return None
