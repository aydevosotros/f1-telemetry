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

type MetricKey = keyof Pick<
  TelemetrySample,
  "speed_kph" | "throttle" | "brake" | "steer" | "engine_rpm" | "gear"
>;

type MetricComparisonChartProps = {
  title: string;
  metric: MetricKey;
  samples: TelemetrySample[];
  comparison: TelemetrySample[];
  primaryLabel: string;
  comparisonLabel: string;
  formatter?: (value: number | null) => number | null;
  unit?: string;
};

export function MetricComparisonChart({
  title,
  metric,
  samples,
  comparison,
  primaryLabel,
  comparisonLabel,
  formatter = (value) => value,
  unit,
}: MetricComparisonChartProps) {
  const startTime = samples[0]?.session_time ?? 0;
  const data = samples.slice(-800).map((sample, index) => {
    const primaryValue = sample[metric] as number | null;
    const comparisonValue = comparison[index]?.[metric] as number | null | undefined;
    return {
      t: Number(((sample.lap_distance ?? sample.session_time - startTime) || 0).toFixed(2)),
      [primaryLabel]: formatter(primaryValue),
      [comparisonLabel]: formatter(comparisonValue ?? null),
    };
  });

  return (
    <section className="metric-chart">
      <div className="metric-chart-header">
        <h2>{title}</h2>
        {unit ? <span>{unit}</span> : null}
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="t" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey={primaryLabel} stroke="#e10600" dot={false} strokeWidth={2} />
          <Line type="monotone" dataKey={comparisonLabel} stroke="#2563eb" dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </section>
  );
}
