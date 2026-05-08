function formatAge(timestamp) {
  if (!timestamp) {
    return "n/a";
  }
  const created = new Date(timestamp);
  const diffMs = Date.now() - created.getTime();
  const minutes = Math.max(Math.floor(diffMs / 60000), 0);
  if (minutes < 1) {
    return "just now";
  }
  if (minutes < 60) {
    return `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

function severityClass(severity) {
  if (!severity) {
    return "p3";
  }
  return severity.toLowerCase();
}

export default function IncidentCard({ incident, active, onSelect }) {
  return (
    <div
      className={`incident-card ${active ? "active" : ""}`}
      onClick={() => onSelect(incident.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          onSelect(incident.id);
        }
      }}
    >
      <div>
        <div className="incident-meta">
          <span className={`badge ${severityClass(incident.severity)}`}>
            {incident.severity || "P3"}
          </span>
          <span className="status-pill">{incident.status}</span>
        </div>
        <h3>{incident.title || `Incident: ${incident.component_id}`}</h3>
        <div className="incident-meta">
          <span>Component: {incident.component_id}</span>
          <span>Signals: {incident.signal_count}</span>
        </div>
      </div>
      <div className="incident-meta">
        <span>Age: {formatAge(incident.created_at)}</span>
      </div>
    </div>
  );
}
