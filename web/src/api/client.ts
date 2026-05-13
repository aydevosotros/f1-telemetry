const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";

export type CaptureState = {
  recording: boolean;
  session_id: string | null;
  udp_host: string;
  udp_port: number;
};

export type SessionSummary = {
  id: string;
  name: string;
  game_year: number;
  track_id: number | null;
  started_at: string;
  ended_at: string | null;
  status: string;
  notes: string | null;
};

export type Driver = {
  id: string;
  game_session_id: string | null;
  car_index: number;
  driver_name: string | null;
  team_name: string | null;
};

export type SessionDetail = SessionSummary & {
  drivers: Driver[];
};

export type TelemetrySample = {
  car_index: number;
  game_session_id: string | null;
  session_time: number;
  speed_kph: number | null;
  throttle: number | null;
  brake: number | null;
  steer: number | null;
  gear: number | null;
  engine_rpm: number | null;
  drs: boolean | null;
  lap_number: number | null;
  lap_distance: number | null;
};

export type LapSummary = {
  game_session_id: string | null;
  car_index: number;
  lap_number: number;
  sample_count: number;
  start_session_time: number;
  end_session_time: number;
  lap_time: number;
  min_lap_distance: number | null;
  max_lap_distance: number | null;
};

export type GameSession = {
  id: string;
  capture_session_id: string;
  session_uid: number;
  session_type: number | null;
  track_id: number | null;
  track_length: number | null;
  started_at: string;
  last_seen_at: string;
};

export type LiveMessage = {
  type: "telemetry";
  session_id: string;
  packet_id: number | null;
  sample_count: number;
  samples: TelemetrySample[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  captureState: () => request<CaptureState>("/capture/state"),
  startCapture: (name?: string) =>
    request<CaptureState>("/capture/start", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  stopCapture: () => request<CaptureState>("/capture/stop", { method: "POST" }),
  sessions: () => request<SessionSummary[]>("/sessions"),
  session: (sessionId: string) => request<SessionDetail>(`/sessions/${sessionId}`),
  gameSessions: (sessionId: string) => request<GameSession[]>(`/sessions/${sessionId}/game-sessions`),
  samples: (sessionId: string, carIndex?: number, lapNumber?: number, gameSessionId?: string) => {
    const params = new URLSearchParams({ limit: "10000" });
    if (gameSessionId) params.set("game_session_id", gameSessionId);
    if (carIndex !== undefined) params.set("car_index", String(carIndex));
    if (lapNumber !== undefined) params.set("lap_number", String(lapNumber));
    return request<TelemetrySample[]>(`/sessions/${sessionId}/samples?${params}`);
  },
  laps: (sessionId: string, carIndex?: number, gameSessionId?: string) => {
    const params = new URLSearchParams();
    if (gameSessionId) params.set("game_session_id", gameSessionId);
    if (carIndex !== undefined) params.set("car_index", String(carIndex));
    const query = params.toString();
    return request<LapSummary[]>(`/sessions/${sessionId}/laps${query ? `?${query}` : ""}`);
  },
  liveSocket: () => new WebSocket(`${wsBaseUrl}/ws/live`),
};
