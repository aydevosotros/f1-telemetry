import type { TelemetrySample } from "./api/client";

export type MetricKey = keyof Pick<
  TelemetrySample,
  "speed_kph" | "throttle" | "brake" | "steer" | "engine_rpm" | "gear"
>;
