import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { TelemetrySample } from "../api/client";

type TelemetryChartProps = {
  samples: TelemetrySample[];
  comparison?: TelemetrySample[];
  primaryLabel?: string;
  comparisonLabel?: string;
  showComparison?: boolean;
};

export function TelemetryChart({
  samples,
  comparison = [],
  primaryLabel = "Primary speed",
  comparisonLabel = "Comparison speed",
  showComparison = true,
}: TelemetryChartProps) {
  const startTime = samples[0]?.session_time ?? 0;
  const data = samples.slice(-500).map((sample, index) => ({
    t: Number(((sample.lap_distance ?? sample.session_time - startTime) || 0).toFixed(2)),
    [primaryLabel]: sample.speed_kph ?? 0,
    throttle: Math.round((sample.throttle ?? 0) * 100),
    brake: Math.round((sample.brake ?? 0) * 100),
    [comparisonLabel]: comparison[index]?.speed_kph ?? null,
  }));

  return (
    <div className="chart-panel">
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="t" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey={primaryLabel} stroke="#e10600" dot={false} strokeWidth={2} />
          <Line type="monotone" dataKey="throttle" stroke="#168a45" dot={false} strokeWidth={1.5} />
          <Line type="monotone" dataKey="brake" stroke="#2563eb" dot={false} strokeWidth={1.5} />
          {showComparison ? (
            <Line
              type="monotone"
              dataKey={comparisonLabel}
              stroke="#f59e0b"
              dot={false}
              strokeWidth={2}
            />
          ) : null}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
