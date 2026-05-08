import { Link } from "react-router-dom";

import Header from "../components/Header";

export default function AnalyticsPage({ connected }) {
  return (
    <>
      <Header connected={connected} />
      <main className="page">
        <div className="chart" style={{ textAlign: "center", padding: "3rem 2rem" }}>
          <div className="section-title" style={{ marginBottom: "1rem" }}>
            Throughput moved
          </div>
          <p style={{ color: "var(--muted)", marginBottom: "1.5rem" }}>
            The Signal Throughput time-series chart now lives on the{" "}
            <strong>Metrics</strong> page alongside live Signals/sec and Avg MTTR stats.
          </p>
          <Link to="/metrics" className="button accent" style={{ textDecoration: "none" }}>
            Go to Metrics →
          </Link>
        </div>
      </main>
    </>
  );
}
