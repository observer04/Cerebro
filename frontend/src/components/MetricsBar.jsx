export default function MetricsBar({ metrics }) {
  return (
    <section className="metrics-bar metrics-bar--single">
      <div className="metric-card">
        <span>Active incidents</span>
        <strong>{metrics.activeIncidents}</strong>
      </div>
    </section>
  );
}
