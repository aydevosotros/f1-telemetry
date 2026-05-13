type MetricCardProps = {
  label: string;
  value: string | number;
  unit?: string;
};

export function MetricCard({ label, value, unit }: MetricCardProps) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>
        {value}
        {unit ? <small>{unit}</small> : null}
      </strong>
    </div>
  );
}
