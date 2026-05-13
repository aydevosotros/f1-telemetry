import { GripVertical, RefreshCw } from "lucide-react";
import { type DragEvent, useEffect, useState } from "react";

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
const chartOrderStorageKey = "f1-telemetry-session-chart-order";

type MetricKey = keyof Pick<
  TelemetrySample,
  "speed_kph" | "throttle" | "brake" | "steer" | "engine_rpm" | "gear"
>;

type MetricConfig = {
  id: string;
  title: string;
  metric: MetricKey;
  formatter?: (value: number | null) => number | null;
  unit?: string;
};

const metricConfigs: MetricConfig[] = [
  { id: "speed", title: "Speed", metric: "speed_kph", unit: "kph" },
  {
    id: "throttle",
    title: "Throttle",
    metric: "throttle",
    formatter: (value) => (value === null ? null : Math.round(value * 100)),
    unit: "%",
  },
  {
    id: "brake",
    title: "Brake",
    metric: "brake",
    formatter: (value) => (value === null ? null : Math.round(value * 100)),
    unit: "%",
  },
  { id: "steering", title: "Steering", metric: "steer" },
  { id: "engine-rpm", title: "Engine RPM", metric: "engine_rpm" },
  { id: "gear", title: "Gear", metric: "gear" },
];

const defaultMetricOrder = metricConfigs.map((metric) => metric.id);

function loadMetricOrder() {
  const stored = window.localStorage.getItem(chartOrderStorageKey);
  if (!stored) return defaultMetricOrder;

  try {
    const parsed = JSON.parse(stored) as string[];
    const known = parsed.filter((metricId) =>
      metricConfigs.some((metric) => metric.id === metricId),
    );
    const missing = defaultMetricOrder.filter((metricId) => !known.includes(metricId));
    return [...known, ...missing];
  } catch {
    return defaultMetricOrder;
  }
}

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
  const [metricOrder, setMetricOrder] = useState(loadMetricOrder);
  const [draggedMetric, setDraggedMetric] = useState<string | null>(null);

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
  const orderedMetrics = metricOrder
    .map((metricId) => metricConfigs.find((metric) => metric.id === metricId))
    .filter((metric): metric is MetricConfig => Boolean(metric));

  const moveMetric = (sourceId: string, targetId: string) => {
    if (sourceId === targetId) return;
    setMetricOrder((current) => {
      const next = [...current];
      const sourceIndex = next.indexOf(sourceId);
      const targetIndex = next.indexOf(targetId);
      if (sourceIndex === -1 || targetIndex === -1) return current;
      const [source] = next.splice(sourceIndex, 1);
      next.splice(targetIndex, 0, source);
      return next;
    });
  };

  const handleChartDrop = (event: DragEvent, targetId: string) => {
    event.preventDefault();
    if (draggedMetric) moveMetric(draggedMetric, targetId);
    setDraggedMetric(null);
  };

  async function refresh() {
    const loaded = await api.sessions();
    setSessions(loaded);
    if (!selected && loaded.length > 0) setSelected(loaded[0].id);
  }

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    window.localStorage.setItem(chartOrderStorageKey, JSON.stringify(metricOrder));
  }, [metricOrder]);

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
          {orderedMetrics.map((chart) => (
            <div
              className={
                draggedMetric && draggedMetric !== chart.id
                  ? "metric-chart-drop-target"
                  : "metric-chart-drop-target idle"
              }
              key={chart.id}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => handleChartDrop(event, chart.id)}
            >
              <MetricComparisonChart
                title={chart.title}
                metric={chart.metric}
                samples={samples}
                comparison={compare}
                primaryLabel={driverLabel(primaryCar)}
                comparisonLabel={driverLabel(comparisonCar)}
                formatter={chart.formatter}
                headerAction={
                  <button
                    aria-label={`Move ${chart.title} chart`}
                    className="drag-handle"
                    draggable
                    onDragEnd={() => setDraggedMetric(null)}
                    onDragStart={() => setDraggedMetric(chart.id)}
                    title="Drag to reorder chart"
                    type="button"
                  >
                    <GripVertical size={18} />
                  </button>
                }
                unit={chart.unit}
              />
            </div>
          ))}
        </div>
      </main>
    </section>
  );
}
