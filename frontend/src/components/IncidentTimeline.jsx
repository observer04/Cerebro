import { useState, useEffect } from "react";
import { api } from "../api/client";

function formatTime(ts) {
  if (!ts) return "—";
  const d = new Date(ts);
  return d.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function TimelineEntry({ event }) {
  return (
    <div className="timeline-entry">
      <div className={`timeline-dot ${event.type}`} />
      <span className="timeline-time">{formatTime(event.timestamp)}</span>
      <span className="timeline-label">{event.label}</span>
      {event.detail && <span className="timeline-detail">{event.detail}</span>}
      {event.signal_count && (
        <div
          className="burst-bar"
          style={{ width: `${Math.min(event.signal_count * 8, 100)}%` }}
          title={`${event.signal_count} signals`}
        />
      )}
    </div>
  );
}

export default function IncidentTimeline({ workItemId }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!workItemId) return;
    let mounted = true;
    setLoading(true);
    setLoaded(false);

    api
      .getWorkItemTimeline(workItemId)
      .then((data) => {
        if (mounted) {
          setEvents(data.events || []);
          setLoaded(true);
        }
      })
      .catch((err) => {
        console.error("Failed to load timeline:", err);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [workItemId]);

  if (loading) {
    return (
      <div className="section">
        <div className="section-title">Timeline</div>
        <div className="empty-state">Loading timeline…</div>
      </div>
    );
  }

  if (loaded && events.length === 0) {
    return (
      <div className="section">
        <div className="section-title">Timeline</div>
        <div className="empty-state">No timeline events.</div>
      </div>
    );
  }

  return (
    <div className="section">
      <div className="section-title">Timeline</div>
      <div className="timeline">
        {events.map((event, idx) => (
          <TimelineEntry key={idx} event={event} />
        ))}
      </div>
    </div>
  );
}
