import { useEffect, useState } from "react";

import { api } from "../api/client";
import Header from "../components/Header";

function toNumber(value) {
  if (typeof value === "number") {
    return value;
  }
  const parsed = Number(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

export default function MetricsPage({ connected }) {
  const [metrics, setMetrics] = useState([]);

  useEffect(() => {
    let active = true;
    api.getDashboardMetrics()
      .then((data) => {
        if (active) {
          setMetrics(Array.isArray(data) ? data : []);
        }
      })
      .catch(() => {
        if (active) {
          setMetrics([]);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const series = metrics
    .filter((item) => item.metric_name === "signals_per_second")
    .slice(0, 12)
    .reverse();

  const maxValue = Math.max(...series.map((item) => toNumber(item.value)), 1);

  return (
    <>
      <Header connected={connected} />
      <main className="page metrics-page">
        <div className="chart">
          <div className="section-title">Signals per second</div>
          <div className="chart-bars">
            {series.map((item) => (
              <div
                key={item.time}
                className="chart-bar"
                style={{ height: `${(toNumber(item.value) / maxValue) * 100}%` }}
                title={`${toNumber(item.value).toFixed(1)}`}
              />
            ))}
          </div>
        </div>
        <div className="chart">
          <div className="section-title">Recent metrics</div>
          {metrics.length ? (
            <ul>
              {metrics.slice(0, 6).map((item) => (
                <li key={`${item.metric_name}-${item.time}`}>
                  {item.metric_name}: {toNumber(item.value).toFixed(2)}
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state">No metrics captured yet.</div>
          )}
        </div>
      </main>
    </>
  );
}
