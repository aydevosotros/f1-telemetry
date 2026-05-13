from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CaptureStartRequest(BaseModel):
    name: str | None = None
    notes: str | None = None


class CaptureState(BaseModel):
    recording: bool
    session_id: UUID | None = None
    udp_host: str
    udp_port: int


class SessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    game_year: int
    track_id: int | None
    started_at: datetime
    ended_at: datetime | None
    status: str
    notes: str | None


class DriverRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_session_id: UUID | None
    car_index: int
    driver_name: str | None
    team_name: str | None


class SessionDetail(SessionSummary):
    drivers: list[DriverRead] = []


class GameSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    capture_session_id: UUID
    session_uid: int
    session_type: int | None
    track_id: int | None
    track_length: int | None
    started_at: datetime
    last_seen_at: datetime


class TelemetrySampleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    car_index: int
    game_session_id: UUID | None
    session_time: float
    speed_kph: int | None
    throttle: float | None
    brake: float | None
    steer: float | None
    gear: int | None
    engine_rpm: int | None
    drs: bool | None
    lap_number: int | None
    lap_distance: float | None


class LapSummaryRead(BaseModel):
    game_session_id: UUID | None
    car_index: int
    lap_number: int
    sample_count: int
    start_session_time: float
    end_session_time: float
    lap_time: float
    min_lap_distance: float | None
    max_lap_distance: float | None
