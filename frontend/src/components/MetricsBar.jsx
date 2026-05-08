function formatSeconds(value) {
  if (!value || value <= 0) {
    return "0s";
  }
  if (value < 60) {
    return `${value.toFixed(0)}s`;
  }
  if (value < 3600) {
    return `${(value / 60).toFixed(1)}m`;
  }
  return `${(value / 3600).toFixed(1)}h`;
}

export default function MetricsBar({ metrics }) {
  return (
    <section className="metrics-bar">
      <div className="metric-card">
        <span>Signals per second</span>
        <strong>{metrics.signalsPerSecond.toFixed(1)}</strong>
      </div>
      <div className="metric-card">
        <span>Active incidents</span>
        <strong>{metrics.activeIncidents}</strong>
      </div>
      <div className="metric-card">
        <span>Avg MTTR</span>
        <strong>{formatSeconds(metrics.avgMttrSeconds)}</strong>
      </div>
    </section>
  );
}
