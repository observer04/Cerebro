import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function SystemHealthBar() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const fetchHealth = async () => {
      try {
        const data = await api.getHealthSummary();
        if (mounted) setHealth(data);
      } catch (err) {
        console.error("Failed to load health summary:", err);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  if (loading || !health) {
    return <div className="health-bar"><div className="empty-state">Loading system health…</div></div>;
  }

  return (
    <div className="health-bar">
      <div className="health-card">
        <span className="health-label">Active Incidents</span>
        <strong className="health-value">{health.active_incidents}</strong>
        <div className="severity-counts">
          {Object.entries(health.by_severity).map(([sev, count]) => (
            count > 0 && (
              <span key={sev} className={`badge ${sev.toLowerCase()}`}>
                {sev}: {count}
              </span>
            )
          ))}
        </div>
      </div>

      <div className="health-card">
        <span className="health-label">Debounce Windows</span>
        <strong className="health-value">{health.debounce_active_windows}</strong>
        <span className="health-sub">Active dedup windows</span>
      </div>

      <div className="health-card">
        <span className="health-label">Avg MTTR</span>
        <strong className="health-value">
          {health.avg_mttr_seconds
            ? `${Math.round(health.avg_mttr_seconds / 60)}m`
            : "—"}
        </strong>
        <span className="health-sub">Mean time to resolve</span>
      </div>

      <div className="health-card">
        <span className="health-label">Throughput</span>
        <strong className="health-value">{health.throughput_total.toLocaleString()}</strong>
        <span className="health-sub">Total signals processed</span>
      </div>
    </div>
  );
}
