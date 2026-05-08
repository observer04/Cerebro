import { useState, useCallback } from "react";
import { api } from "../api/client";

function formatTimestamp(ts) {
  if (!ts) return "—";
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function SignalCard({ signal }) {
  const [expanded, setExpanded] = useState(false);
  const hasMeta = signal.metadata && Object.keys(signal.metadata).length > 0;

  return (
    <div className="signal-card">
      <div className="signal-header" onClick={() => hasMeta && setExpanded(!expanded)}>
        <span className="signal-time">{formatTimestamp(signal.timestamp)}</span>
        <span className="signal-source">{signal.source || "unknown"}</span>
        {signal.severity_hint && (
          <span className={`badge ${signal.severity_hint.toLowerCase()}`}>
            {signal.severity_hint}
          </span>
        )}
        {hasMeta && (
          <span className="signal-expand-icon">{expanded ? "▾" : "▸"}</span>
        )}
      </div>
      {expanded && hasMeta && (
        <pre className="signal-metadata">
          {JSON.stringify(signal.metadata, null, 2)}
        </pre>
      )}
    </div>
  );
}

export default function SignalDrawer({ workItemId }) {
  const [open, setOpen] = useState(false);
  const [signals, setSignals] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [skip, setSkip] = useState(0);
  const limit = 50;

  const fetchSignals = useCallback(
    async (currentSkip = 0, append = false) => {
      setLoading(true);
      try {
        const data = await api.getWorkItemSignals(workItemId, {
          limit,
          skip: currentSkip,
        });
        setSignals((prev) => (append ? [...prev, ...data.signals] : data.signals));
        setTotal(data.total);
        setSkip(currentSkip + data.signals.length);
        setLoaded(true);
      } catch (err) {
        console.error("Failed to load signals:", err);
      } finally {
        setLoading(false);
      }
    },
    [workItemId]
  );

  const handleToggle = () => {
    const willOpen = !open;
    setOpen(willOpen);
    if (willOpen && !loaded) {
      fetchSignals(0);
    }
  };

  const handleLoadMore = () => {
    fetchSignals(skip, true);
  };

  return (
    <div className="section signal-drawer">
      <button
        className="signal-drawer-toggle"
        onClick={handleToggle}
        type="button"
      >
        <span className="section-title">
          Raw Signals {loaded ? `(${total})` : ""}
        </span>
        <span className="signal-expand-icon">{open ? "▾" : "▸"}</span>
      </button>

      {open && (
        <div className="signal-drawer-content">
          {loading && signals.length === 0 && (
            <div className="empty-state">Loading signals…</div>
          )}
          {loaded && signals.length === 0 && (
            <div className="empty-state">No raw signals found for this incident.</div>
          )}
          {signals.map((sig, idx) => (
            <SignalCard key={sig.signal_id || idx} signal={sig} />
          ))}
          {loaded && skip < total && (
            <button
              className="button secondary"
              onClick={handleLoadMore}
              disabled={loading}
              type="button"
            >
              {loading ? "Loading…" : `Load more (${total - skip} remaining)`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
