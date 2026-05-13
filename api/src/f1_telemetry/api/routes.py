import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from f1_telemetry.core.config import settings
from f1_telemetry.db.session import get_db
from f1_telemetry.schemas.telemetry import (
    CaptureStartRequest,
    CaptureState,
    GameSessionRead,
    LapSummaryRead,
    SessionDetail,
    SessionSummary,
    TelemetrySampleRead,
)
from f1_telemetry.services.capture import capture_manager
from f1_telemetry.services.hub import hub
from f1_telemetry.services.sessions import session_service

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]
GameSessionQuery = Annotated[UUID | None, Query()]
CarIndexQuery = Annotated[int | None, Query(ge=0, le=21)]
LapNumberQuery = Annotated[int | None, Query(ge=0)]
SampleLimitQuery = Annotated[int, Query(ge=1, le=100_000)]


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/capture/state", response_model=CaptureState)
async def capture_state() -> CaptureState:
    return CaptureState(
        recording=capture_manager.recording,
        session_id=capture_manager.session_id,
        udp_host=settings.udp_host,
        udp_port=settings.udp_port,
    )


@router.post("/capture/start", response_model=CaptureState)
async def start_capture(payload: CaptureStartRequest, db: DbSession) -> CaptureState:
    if capture_manager.recording:
        raise HTTPException(status_code=409, detail="Capture is already running")
    session = await session_service.create_session(db, payload.name, payload.notes)
    await capture_manager.start(session.id)
    return await capture_state()


@router.post("/capture/stop", response_model=CaptureState)
async def stop_capture(db: DbSession) -> CaptureState:
    session_id = await capture_manager.stop()
    if session_id is not None:
        await session_service.finish_session(db, session_id)
    return await capture_state()


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(db: DbSession) -> list[SessionSummary]:
    return await session_service.list_sessions(db)


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: UUID, db: DbSession) -> SessionDetail:
    session = await session_service.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions/{session_id}/game-sessions", response_model=list[GameSessionRead])
async def list_game_sessions(
    session_id: UUID,
    db: DbSession,
) -> list[GameSessionRead]:
    return await session_service.list_game_sessions(db, session_id)


@router.get("/sessions/{session_id}/samples", response_model=list[TelemetrySampleRead])
async def list_samples(
    session_id: UUID,
    db: DbSession,
    game_session_id: GameSessionQuery = None,
    car_index: CarIndexQuery = None,
    lap_number: LapNumberQuery = None,
    limit: SampleLimitQuery = 5000,
) -> list[TelemetrySampleRead]:
    return await session_service.list_samples(
        db,
        session_id,
        game_session_id,
        car_index,
        lap_number,
        limit,
    )


@router.get("/sessions/{session_id}/laps", response_model=list[LapSummaryRead])
async def list_laps(
    session_id: UUID,
    db: DbSession,
    game_session_id: GameSessionQuery = None,
    car_index: CarIndexQuery = None,
) -> list[LapSummaryRead]:
    return await session_service.list_laps(db, session_id, game_session_id, car_index)


@router.websocket("/ws/live")
async def live_socket(websocket: WebSocket) -> None:
    await hub.connect_live(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect_live(websocket)


@router.websocket("/ws/replay/{session_id}")
async def replay_socket(websocket: WebSocket, session_id: UUID) -> None:
    await hub.connect_session(session_id, websocket)
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        await hub.disconnect_session(session_id, websocket)
