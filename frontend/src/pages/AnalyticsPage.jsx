import { useEffect, useState, useRef } from "react";
import { api } from "../api/client";
import Header from "../components/Header";

const INTERVALS = ["5 minutes", "1 hour", "1 day"];
const HOUR_OPTIONS = [6, 12, 24, 48, 168];

function ThroughputChart({ buckets }) {
  const containerRef = useRef(null);

  if (!buckets || buckets.length === 0) {
    return <div className="empty-state">No throughput data available.</div>;
  }

  const maxSignals = Math.max(...buckets.map((b) => b.signals), 1);
  const maxIncidents = Math.max(...buckets.map((b) => b.incidents), 1);
  const maxVal = Math.max(maxSignals, maxIncidents);

  const W = 800;
  const H = 220;
  const padL = 50;
  const padR = 20;
  const padT = 15;
  const padB = 30;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;

  const xStep = chartW / Math.max(buckets.length - 1, 1);

  const signalPoints = buckets
    .map((b, i) => {
      const x = padL + i * xStep;
      const y = padT + chartH - (b.signals / maxVal) * chartH;
      return `${x},${y}`;
    })
    .join(" ");

  const incidentPoints = buckets
    .map((b, i) => {
      const x = padL + i * xStep;
      const y = padT + chartH - (b.incidents / maxVal) * chartH;
      return `${x},${y}`;
    })
    .join(" ");

  // Area fill for signals
  const signalArea = `${padL},${padT + chartH} ${signalPoints} ${padL + (buckets.length - 1) * xStep},${padT + chartH}`;

  // Y-axis gridlines
  const gridLines = [0, 0.25, 0.5, 0.75, 1].map((pct) => {
    const y = padT + chartH - pct * chartH;
    const val = Math.round(pct * maxVal);
    return { y, val };
  });

  return (
    <div className="chart-area" ref={containerRef}>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        {/* Grid lines */}
        {gridLines.map((g) => (
          <g key={g.val}>
            <line
              x1={padL}
              y1={g.y}
              x2={W - padR}
              y2={g.y}
              stroke="rgba(0,0,0,0.06)"
              strokeWidth="1"
            />
            <text
              x={padL - 8}
              y={g.y + 4}
              textAnchor="end"
              fill="#6b6258"
              fontSize="9"
              fontFamily="IBM Plex Mono, monospace"
            >
              {g.val}
            </text>
          </g>
        ))}

        {/* Signal area fill */}
        <polygon
          points={signalArea}
          fill="url(#signalGradient)"
          opacity="0.15"
        />

        {/* Signal line */}
        <polyline
          points={signalPoints}
          fill="none"
          stroke="#ff6b35"
          strokeWidth="2"
          strokeLinejoin="round"
        />

        {/* Incident line */}
        <polyline
          points={incidentPoints}
          fill="none"
          stroke="#12b886"
          strokeWidth="2"
          strokeLinejoin="round"
          strokeDasharray="6,3"
        />

        {/* Signal dots */}
        {buckets.map((b, i) => {
          const x = padL + i * xStep;
          const y = padT + chartH - (b.signals / maxVal) * chartH;
          return <circle key={`s-${i}`} cx={x} cy={y} r="3" fill="#ff6b35" />;
        })}

        {/* Gradient definition */}
        <defs>
          <linearGradient id="signalGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ff6b35" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#ff6b35" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>

      {/* Legend */}
      <div
        style={{
          display: "flex",
          gap: "1.5rem",
          justifyContent: "center",
          marginTop: "0.5rem",
          fontSize: "0.78rem",
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
          <span
            style={{
              width: 12,
              height: 3,
              background: "#ff6b35",
              borderRadius: 2,
            }}
          />
          Signals
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
          <span
            style={{
              width: 12,
              height: 3,
              background: "#12b886",
              borderRadius: 2,
              borderTop: "1px dashed #12b886",
            }}
          />
          Incidents
        </span>
      </div>
    </div>
  );
}

export default function AnalyticsPage({ connected }) {
  const [interval, setInterval_] = useState("1 hour");
  const [hours, setHours] = useState(24);
  const [buckets, setBuckets] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);

    api
      .getAnalyticsThroughput({ interval, hours })
      .then((data) => {
        if (mounted) setBuckets(data.buckets || []);
      })
      .catch((err) => console.error("Analytics load failed:", err))
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [interval, hours]);

  return (
    <>
      <Header connected={connected} />
      <main className="page">
        <div className="chart">
          <div className="section-title">Signal Throughput — Time Series</div>

          <div className="analytics-controls">
            <div className="control-group">
              <label>Bucket</label>
              {INTERVALS.map((iv) => (
                <button
                  key={iv}
                  className={`chip ${interval === iv ? "active" : ""}`}
                  onClick={() => setInterval_(iv)}
                  type="button"
                >
                  {iv}
                </button>
              ))}
            </div>

            <div className="control-group">
              <label>Range</label>
              {HOUR_OPTIONS.map((h) => (
                <button
                  key={h}
                  className={`chip ${hours === h ? "active" : ""}`}
                  onClick={() => setHours(h)}
                  type="button"
                >
                  {h}h
                </button>
              ))}
            </div>
          </div>

          {loading ? (
            <div className="empty-state">Loading analytics…</div>
          ) : (
            <ThroughputChart buckets={buckets} />
          )}
        </div>
      </main>
    </>
  );
}
