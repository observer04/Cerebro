import { useEffect, useRef, useState, useMemo } from "react";

import { api } from "../api/client";
import Header from "../components/Header";

// ── helpers ──────────────────────────────────────────────────────────────────

function formatSeconds(value) {
  if (!value || value <= 0) return "—";
  if (value < 60) return `${value.toFixed(0)}s`;
  if (value < 3600) return `${(value / 60).toFixed(1)}m`;
  return `${(value / 3600).toFixed(1)}h`;
}

// ── 1. Real-Time Signal Bar Graph ─────────────────────────────────────────────

const BAR_HISTORY = 30;   // keep last 30 readings

function LiveBarGraph({ stream }) {
  const [history, setHistory] = useState([]);
  const prevRate = useRef(null);

  useEffect(() => {
    const rate = stream?.metrics?.signalsPerSecond ?? 0;
    // Only push when the value actually changes (new SSE event)
    if (rate !== prevRate.current) {
      prevRate.current = rate;
      setHistory((prev) => {
        const next = [...prev, { time: Date.now(), value: rate }];
        return next.slice(-BAR_HISTORY);
      });
    }
  }, [stream?.metrics?.signalsPerSecond]);

  // Also push periodically so the graph keeps moving even at 0
  useEffect(() => {
    const id = setInterval(() => {
      setHistory((prev) => {
        const next = [...prev, { time: Date.now(), value: stream?.metrics?.signalsPerSecond ?? 0 }];
        return next.slice(-BAR_HISTORY);
      });
    }, 5000);
    return () => clearInterval(id);
  }, [stream?.metrics?.signalsPerSecond]);

  const maxVal = Math.max(...history.map((h) => h.value), 1);

  return (
    <div className="chart">
      <div className="section-title">Live Signal Throughput</div>
      <div className="live-bar-label">
        <strong>{(stream?.metrics?.signalsPerSecond ?? 0).toFixed(1)}</strong>
        <span> signals/sec</span>
      </div>
      <div className="chart-bars">
        {history.map((h, i) => (
          <div
            key={`${h.time}-${i}`}
            className="chart-bar"
            style={{ height: `${Math.max((h.value / maxVal) * 100, 2)}%` }}
            title={`${h.value.toFixed(1)} sig/s`}
          />
        ))}
        {/* fill empty slots */}
        {Array.from({ length: Math.max(BAR_HISTORY - history.length, 0) }).map((_, i) => (
          <div key={`empty-${i}`} className="chart-bar" style={{ height: "2%" }} />
        ))}
      </div>
    </div>
  );
}

// ── 2. Throughput Time-Series (fix: handle empty data + different bucket) ─────

const INTERVALS = ["5 minutes", "1 hour", "1 day"];
const HOUR_OPTIONS = [6, 12, 24, 48, 168];

function ThroughputChart({ buckets }) {
  if (!buckets || buckets.length === 0) {
    return <div className="empty-state">No throughput data available. Run demo traffic to populate.</div>;
  }

  const maxSignals   = Math.max(...buckets.map((b) => b.signals ?? 0), 1);
  const maxIncidents = Math.max(...buckets.map((b) => b.incidents ?? 0), 1);
  const maxVal       = Math.max(maxSignals, maxIncidents);

  const W = 800; const H = 220;
  const padL = 50; const padR = 20; const padT = 15; const padB = 30;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;
  const xStep  = chartW / Math.max(buckets.length - 1, 1);

  const signalPoints = buckets
    .map((b, i) => `${padL + i * xStep},${padT + chartH - ((b.signals ?? 0) / maxVal) * chartH}`)
    .join(" ");

  const incidentPoints = buckets
    .map((b, i) => `${padL + i * xStep},${padT + chartH - ((b.incidents ?? 0) / maxVal) * chartH}`)
    .join(" ");

  const signalArea =
    `${padL},${padT + chartH} ${signalPoints} ${padL + (buckets.length - 1) * xStep},${padT + chartH}`;

  const gridLines = [0, 0.25, 0.5, 0.75, 1].map((pct) => ({
    y:   padT + chartH - pct * chartH,
    val: Math.round(pct * maxVal),
  }));

  return (
    <div className="chart-area">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id="signalGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#ff6b35" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#ff6b35" stopOpacity="0"   />
          </linearGradient>
        </defs>

        {gridLines.map((g) => (
          <g key={g.val}>
            <line x1={padL} y1={g.y} x2={W - padR} y2={g.y}
              stroke="rgba(0,0,0,0.06)" strokeWidth="1" />
            <text x={padL - 8} y={g.y + 4} textAnchor="end"
              fill="#6b6258" fontSize="9" fontFamily="IBM Plex Mono, monospace">
              {g.val}
            </text>
          </g>
        ))}

        <polygon points={signalArea} fill="url(#signalGradient)" opacity="0.15" />

        <polyline points={signalPoints} fill="none"
          stroke="#ff6b35" strokeWidth="2" strokeLinejoin="round" />

        <polyline points={incidentPoints} fill="none"
          stroke="#12b886" strokeWidth="2" strokeLinejoin="round" strokeDasharray="6,3" />

        {buckets.map((b, i) => {
          const x = padL + i * xStep;
          const y = padT + chartH - ((b.signals ?? 0) / maxVal) * chartH;
          return <circle key={`s-${i}`} cx={x} cy={y} r="3" fill="#ff6b35" />;
        })}
      </svg>

      <div style={{ display: "flex", gap: "1.5rem", justifyContent: "center",
                    marginTop: "0.5rem", fontSize: "0.78rem" }}>
        <span style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
          <span style={{ width: 12, height: 3, background: "#ff6b35", borderRadius: 2 }} />
          Signals
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
          <span style={{ width: 12, height: 3, background: "#12b886", borderRadius: 2,
                         borderTop: "1px dashed #12b886" }} />
          Incidents
        </span>
      </div>
    </div>
  );
}

// ── 3. Severity Distribution ──────────────────────────────────────────────────

const SEV_COLORS = { P0: "#d62828", P1: "#f77f00", P2: "#2a9d8f", P3: "#3a86ff" };

function SeverityDistribution({ components }) {
  const counts = useMemo(() => {
    const sev = { P0: 0, P1: 0, P2: 0, P3: 0 };
    // We use component-health data to derive, but actually use work-items
    // So let's compute from the SystemHealthBar data instead
    return sev;
  }, [components]);

  // We'll use a different data source: system health summary
  const [data, setData] = useState(null);

  useEffect(() => {
    api.getHealthSummary()
      .then((d) => setData(d))
      .catch(() => {});
    const id = setInterval(() => {
      api.getHealthSummary().then((d) => setData(d)).catch(() => {});
    }, 15000);
    return () => clearInterval(id);
  }, []);

  const sevCounts = data?.by_severity || {};
  const total = Object.values(sevCounts).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="chart analytics-panel">
      <div className="section-title">Severity Distribution</div>
      <div className="severity-bars">
        {["P0", "P1", "P2", "P3"].map((sev) => {
          const count = sevCounts[sev] || 0;
          const pct = ((count / total) * 100).toFixed(0);
          return (
            <div key={sev} className="severity-row">
              <span className={`badge ${sev.toLowerCase()}`}>{sev}</span>
              <div className="severity-track">
                <div
                  className="severity-fill"
                  style={{
                    width: `${Math.max(pct, 2)}%`,
                    background: SEV_COLORS[sev],
                  }}
                />
              </div>
              <span className="severity-count">{count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── 4. MTTR by Component ──────────────────────────────────────────────────────

function MttrByComponent({ componentData }) {
  if (!componentData || componentData.length === 0) {
    return (
      <div className="chart analytics-panel">
        <div className="section-title">MTTR by Component</div>
        <div className="empty-state">No MTTR data available.</div>
      </div>
    );
  }

  const withMttr = componentData.filter((c) => c.avg_mttr_seconds > 0);
  if (withMttr.length === 0) {
    return (
      <div className="chart analytics-panel">
        <div className="section-title">MTTR by Component</div>
        <div className="empty-state">No resolved incidents yet.</div>
      </div>
    );
  }

  const maxMttr = Math.max(...withMttr.map((c) => c.avg_mttr_seconds), 1);

  return (
    <div className="chart analytics-panel">
      <div className="section-title">MTTR by Component</div>
      <div className="mttr-bars">
        {withMttr.slice(0, 8).map((c) => (
          <div key={c.component_id} className="mttr-row">
            <span className="mttr-label">{c.component_id}</span>
            <div className="mttr-track">
              <div
                className="mttr-fill"
                style={{ width: `${(c.avg_mttr_seconds / maxMttr) * 100}%` }}
              />
            </div>
            <span className="mttr-value">{formatSeconds(c.avg_mttr_seconds)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── 5. Incident Volume by Component ───────────────────────────────────────────

function IncidentVolume({ componentData }) {
  if (!componentData || componentData.length === 0) {
    return (
      <div className="chart analytics-panel">
        <div className="section-title">Incident Volume by Component</div>
        <div className="empty-state">No incident data available.</div>
      </div>
    );
  }

  const maxTotal = Math.max(...componentData.map((c) => c.total_incidents), 1);

  return (
    <div className="chart analytics-panel">
      <div className="section-title">Incident Volume by Component</div>
      <div className="volume-bars">
        {componentData.slice(0, 8).map((c) => (
          <div key={c.component_id} className="volume-row">
            <span className="volume-label">{c.component_id}</span>
            <div className="volume-track">
              <div
                className="volume-fill volume-active"
                style={{ width: `${(c.active_incidents / maxTotal) * 100}%` }}
              />
              <div
                className="volume-fill volume-total"
                style={{ width: `${((c.total_incidents - c.active_incidents) / maxTotal) * 100}%` }}
              />
            </div>
            <span className="volume-value">
              {c.active_incidents} / {c.total_incidents}
            </span>
          </div>
        ))}
      </div>
      <div className="volume-legend">
        <span><span className="dot active-dot" /> Active</span>
        <span><span className="dot total-dot" /> Resolved</span>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function MetricsPage({ connected, stream }) {
  const [interval, setInterval_] = useState("1 hour");
  const [hours, setHours]       = useState(24);
  const [buckets, setBuckets]   = useState([]);
  const [loading, setLoading]   = useState(true);
  const [componentData, setComponentData] = useState([]);

  // Throughput time-series (from analytics API)
  useEffect(() => {
    let mounted = true;
    setLoading(true);
    api
      .getAnalyticsThroughput({ interval, hours })
      .then((data) => { if (mounted) setBuckets(data.buckets || []); })
      .catch((err) => console.error("Throughput load failed:", err))
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [interval, hours]);

  // Component health for analytics panels
  useEffect(() => {
    api.getComponentHealth()
      .then((data) => setComponentData(data.components || []))
      .catch(() => {});
  }, []);

  return (
    <>
      <Header connected={connected} />
      <main className="page metrics-page">

        {/* Live real-time bar graph */}
        {stream && <LiveBarGraph stream={stream} />}

        {/* Throughput time-series */}
        <div className="chart">
          <div className="section-title">Signal Throughput — Time Series</div>

          <div className="analytics-controls">
            <div className="control-group">
              <label>Bucket</label>
              {INTERVALS.map((iv) => (
                <button key={iv} type="button"
                  className={`chip ${interval === iv ? "active" : ""}`}
                  onClick={() => setInterval_(iv)}>
                  {iv}
                </button>
              ))}
            </div>
            <div className="control-group">
              <label>Range</label>
              {HOUR_OPTIONS.map((h) => (
                <button key={h} type="button"
                  className={`chip ${hours === h ? "active" : ""}`}
                  onClick={() => setHours(h)}>
                  {h}h
                </button>
              ))}
            </div>
          </div>

          {loading
            ? <div className="empty-state">Loading throughput…</div>
            : <ThroughputChart buckets={buckets} />}
        </div>

        {/* 3 Analytics panels */}
        <div className="analytics-grid">
          <SeverityDistribution />
          <MttrByComponent componentData={componentData} />
          <IncidentVolume componentData={componentData} />
        </div>
      </main>
    </>
  );
}
