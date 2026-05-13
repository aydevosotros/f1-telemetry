import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

import {
  api,
  type Driver,
  type GameSession,
  type LapSummary,
  type SessionSummary,
  type TelemetrySample,
} from "../api/client";
import { MetricComparisonChart } from "../components/MetricComparisonChart";

const carIndexes = Array.from({ length: 22 }, (_, index) => index);

export function SessionsPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [gameSessions, setGameSessions] = useState<GameSession[]>([]);
  const [selectedGameSession, setSelectedGameSession] = useState<string | null>(null);
  const [primaryCar, setPrimaryCar] = useState(0);
  const [comparisonCar, setComparisonCar] = useState(1);
  const [primaryLap, setPrimaryLap] = useState<number | null>(null);
  const [comparisonLap, setComparisonLap] = useState<number | null>(null);
  const [primaryLaps, setPrimaryLaps] = useState<LapSummary[]>([]);
  const [comparisonLaps, setComparisonLaps] = useState<LapSummary[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [samples, setSamples] = useState<TelemetrySample[]>([]);
  const [compare, setCompare] = useState<TelemetrySample[]>([]);

  const driverLabel = (carIndex: number) => {
    const driver = drivers.find(
      (item) =>
        item.car_index === carIndex &&
        (!selectedGameSession || item.game_session_id === selectedGameSession),
    );
    return driver?.driver_name || "Driver unavailable";
  };

  const scopedDrivers = selectedGameSession
    ? drivers.filter((driver) => driver.game_session_id === selectedGameSession)
    : drivers;
  const selectableCars =
    scopedDrivers.length > 0
      ? scopedDrivers.map((driver) => driver.car_index).sort((a, b) => a - b)
      : carIndexes;

  async function refresh() {
    const loaded = await api.sessions();
    setSessions(loaded);
    if (!selected && loaded.length > 0) setSelected(loaded[0].id);
  }

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (!selected) return;
    api.session(selected).then((session) => setDrivers(session.drivers));
    api.gameSessions(selected).then((items) => {
      setGameSessions(items);
      setSelectedGameSession((current) =>
        current && items.some((item) => item.id === current) ? current : (items[0]?.id ?? null),
      );
    });
  }, [selected]);

  useEffect(() => {
    if (!selected) return;
    api.laps(selected, primaryCar, selectedGameSession ?? undefined).then((laps) => {
      setPrimaryLaps(laps);
      setPrimaryLap((current) =>
        current !== null && laps.some((lap) => lap.lap_number === current)
          ? current
          : (laps[0]?.lap_number ?? null),
      );
    });
  }, [selected, selectedGameSession, primaryCar]);

  useEffect(() => {
    if (!selected) return;
    api.laps(selected, comparisonCar, selectedGameSession ?? undefined).then((laps) => {
      setComparisonLaps(laps);
      setComparisonLap((current) =>
        current !== null && laps.some((lap) => lap.lap_number === current)
          ? current
          : (laps[0]?.lap_number ?? null),
      );
    });
  }, [selected, selectedGameSession, comparisonCar]);

  useEffect(() => {
    if (!selected || primaryLap === null) {
      setSamples([]);
      return;
    }
    api.samples(selected, primaryCar, primaryLap, selectedGameSession ?? undefined).then(setSamples);
  }, [selected, selectedGameSession, primaryCar, primaryLap]);

  useEffect(() => {
    if (!selected || comparisonLap === null) {
      setCompare([]);
      return;
    }
    api.samples(selected, comparisonCar, comparisonLap, selectedGameSession ?? undefined).then(
      setCompare,
    );
  }, [selected, selectedGameSession, comparisonCar, comparisonLap]);

  const gameSessionLabel = (gameSession: GameSession) => {
    const type = gameSession.session_type === null ? "Session" : `Session ${gameSession.session_type}`;
    return `${type} - ${new Date(gameSession.started_at).toLocaleTimeString()}`;
  };

  return (
    <section className="sessions-layout">
      <aside className="session-list">
        <div className="side-header">
          <h1>Sessions</h1>
          <button className="icon-button" onClick={refresh} title="Refresh sessions">
            <RefreshCw size={18} />
          </button>
        </div>
        {sessions.map((session) => (
          <button
            className={session.id === selected ? "session-row active" : "session-row"}
            key={session.id}
            onClick={() => setSelected(session.id)}
          >
            <strong>{session.name}</strong>
            <span>{new Date(session.started_at).toLocaleString()}</span>
          </button>
        ))}
      </aside>

      <main className="page-grid">
        <div className="toolbar">
          <div>
            <h1>Replay & Compare</h1>
            <p>
              {driverLabel(primaryCar)} lap {primaryLap ?? "-"} against{" "}
              {driverLabel(comparisonCar)} lap {comparisonLap ?? "-"}
            </p>
          </div>
          <div className="compare-controls">
            <label>
              Game session
              <select
                value={selectedGameSession ?? ""}
                onChange={(event) => setSelectedGameSession(event.target.value || null)}
                disabled={gameSessions.length === 0}
              >
                {gameSessions.length === 0 ? <option value="">No game sessions</option> : null}
                {gameSessions.map((gameSession) => (
                  <option key={gameSession.id} value={gameSession.id}>
                    {gameSessionLabel(gameSession)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Primary car
              <select value={primaryCar} onChange={(event) => setPrimaryCar(Number(event.target.value))}>
                {selectableCars.map((carIndex) => (
                  <option key={carIndex} value={carIndex}>
                    {driverLabel(carIndex)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Primary lap
              <select
                value={primaryLap ?? ""}
                onChange={(event) => setPrimaryLap(Number(event.target.value))}
                disabled={primaryLaps.length === 0}
              >
                {primaryLaps.length === 0 ? <option value="">No laps</option> : null}
                {primaryLaps.map((lap) => (
                  <option key={lap.lap_number} value={lap.lap_number}>
                    Lap {lap.lap_number} ({lap.lap_time.toFixed(2)}s)
                  </option>
                ))}
              </select>
            </label>
            <label>
              Compare car
              <select
                value={comparisonCar}
                onChange={(event) => setComparisonCar(Number(event.target.value))}
              >
                {selectableCars.map((carIndex) => (
                  <option key={carIndex} value={carIndex}>
                    {driverLabel(carIndex)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Compare lap
              <select
                value={comparisonLap ?? ""}
                onChange={(event) => setComparisonLap(Number(event.target.value))}
                disabled={comparisonLaps.length === 0}
              >
                {comparisonLaps.length === 0 ? <option value="">No laps</option> : null}
                {comparisonLaps.map((lap) => (
                  <option key={lap.lap_number} value={lap.lap_number}>
                    Lap {lap.lap_number} ({lap.lap_time.toFixed(2)}s)
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
        <div className="metric-chart-grid">
          <MetricComparisonChart
            title="Speed"
            metric="speed_kph"
            samples={samples}
            comparison={compare}
            primaryLabel={driverLabel(primaryCar)}
            comparisonLabel={driverLabel(comparisonCar)}
            unit="kph"
          />
          <MetricComparisonChart
            title="Throttle"
            metric="throttle"
            samples={samples}
            comparison={compare}
            primaryLabel={driverLabel(primaryCar)}
            comparisonLabel={driverLabel(comparisonCar)}
            formatter={(value) => (value === null ? null : Math.round(value * 100))}
            unit="%"
          />
          <MetricComparisonChart
            title="Brake"
            metric="brake"
            samples={samples}
            comparison={compare}
            primaryLabel={driverLabel(primaryCar)}
            comparisonLabel={driverLabel(comparisonCar)}
            formatter={(value) => (value === null ? null : Math.round(value * 100))}
            unit="%"
          />
          <MetricComparisonChart
            title="Steering"
            metric="steer"
            samples={samples}
            comparison={compare}
            primaryLabel={driverLabel(primaryCar)}
            comparisonLabel={driverLabel(comparisonCar)}
          />
          <MetricComparisonChart
            title="Engine RPM"
            metric="engine_rpm"
            samples={samples}
            comparison={compare}
            primaryLabel={driverLabel(primaryCar)}
            comparisonLabel={driverLabel(comparisonCar)}
          />
          <MetricComparisonChart
            title="Gear"
            metric="gear"
            samples={samples}
            comparison={compare}
            primaryLabel={driverLabel(primaryCar)}
            comparisonLabel={driverLabel(comparisonCar)}
          />
        </div>
      </main>
    </section>
  );
}
