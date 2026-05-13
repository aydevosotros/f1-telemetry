import { Radio, Square } from "lucide-react";
import { useEffect, useState } from "react";

import { api, type CaptureState, type Driver, type LiveMessage, type TelemetrySample } from "../api/client";
import { MetricCard } from "../components/MetricCard";
import { TelemetryChart } from "../components/TelemetryChart";

const defaultCars = [0];

export function LivePage() {
  const [state, setState] = useState<CaptureState | null>(null);
  const [samplesByCar, setSamplesByCar] = useState<Record<number, TelemetrySample[]>>({});
  const [selectedCars, setSelectedCars] = useState<number[]>(defaultCars);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.captureState().then(setState).catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!state?.session_id) {
      setDrivers([]);
      return;
    }
    const loadDrivers = () => {
      api.session(state.session_id!).then((session) => setDrivers(session.drivers)).catch(() => {});
    };
    loadDrivers();
    const interval = window.setInterval(loadDrivers, 3000);
    return () => window.clearInterval(interval);
  }, [state?.session_id]);

  useEffect(() => {
    const socket = api.liveSocket();
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data) as LiveMessage;
      if (message.type === "telemetry") {
        setSamplesByCar((current) => {
          const next = { ...current };
          for (const sample of message.samples) {
            next[sample.car_index] = [...(next[sample.car_index] ?? []), sample].slice(-1000);
          }
          return next;
        });
      }
    };
    return () => socket.close();
  }, []);

  const visibleCars = drivers
    .filter((driver) => driver.driver_name)
    .map((driver) => driver.car_index)
    .sort((a, b) => a - b);

  const driverLabel = (carIndex: number) => {
    const driver = drivers.find((item) => item.car_index === carIndex);
    return driver?.driver_name || "Driver unavailable";
  };

  const primarySamples = samplesByCar[selectedCars[0] ?? 0] ?? [];
  const latest = primarySamples.at(-1);
  const totalSamples = Object.values(samplesByCar).reduce((total, samples) => total + samples.length, 0);

  function toggleCar(carIndex: number) {
    setSelectedCars((current) => {
      if (current.includes(carIndex)) {
        const next = current.filter((item) => item !== carIndex);
        return next.length > 0 ? next : current;
      }
      return [...current, carIndex].sort((a, b) => a - b);
    });
  }

  async function start() {
    setError(null);
    try {
      setState(await api.startCapture());
      setSamplesByCar({});
      setDrivers([]);
      setSelectedCars(defaultCars);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start capture");
    }
  }

  async function stop() {
    setError(null);
    try {
      setState(await api.stopCapture());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not stop capture");
    }
  }

  return (
    <section className="page-grid">
      <div className="toolbar">
        <div>
          <h1>Live Capture</h1>
          <p>UDP {state?.udp_host ?? "0.0.0.0"}:{state?.udp_port ?? 20777}</p>
        </div>
        <button className="primary-button" onClick={state?.recording ? stop : start}>
          {state?.recording ? <Square size={18} /> : <Radio size={18} />}
          {state?.recording ? "Stop" : "Start"}
        </button>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}

      <div className="metrics-grid">
        <MetricCard label="Speed" value={latest?.speed_kph ?? 0} unit="kph" />
        <MetricCard label="Throttle" value={Math.round((latest?.throttle ?? 0) * 100)} unit="%" />
        <MetricCard label="Brake" value={Math.round((latest?.brake ?? 0) * 100)} unit="%" />
        <MetricCard label="Gear" value={latest?.gear ?? "-"} />
        <MetricCard label="RPM" value={latest?.engine_rpm ?? 0} />
        <MetricCard label="Samples" value={totalSamples} />
      </div>

      <div className="driver-monitor-panel">
        {visibleCars.length > 0 ? (
          visibleCars.map((carIndex) => (
            <label className="driver-toggle" key={carIndex}>
              <input
                type="checkbox"
                checked={selectedCars.includes(carIndex)}
                onChange={() => toggleCar(carIndex)}
              />
              <span>{driverLabel(carIndex)}</span>
            </label>
          ))
        ) : (
          <div className="empty-state">Driver names will appear after participant data is received.</div>
        )}
      </div>

      <div className="live-chart-grid">
        {selectedCars.map((carIndex) => (
          <section className="driver-chart" key={carIndex}>
            <div className="driver-chart-header">
              <h2>{driverLabel(carIndex)}</h2>
              <span>{samplesByCar[carIndex]?.at(-1)?.speed_kph ?? 0} kph</span>
            </div>
            <TelemetryChart
              samples={samplesByCar[carIndex] ?? []}
              primaryLabel={`${driverLabel(carIndex)} speed`}
              showComparison={false}
            />
          </section>
        ))}
      </div>
    </section>
  );
}
