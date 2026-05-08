function formatAge(timestamp) {
  if (!timestamp) return "n/a";
  const created = new Date(timestamp);
  const diffMs = Date.now() - created.getTime();
  const minutes = Math.max(Math.floor(diffMs / 60000), 0);
  if (minutes < 1) return "now";
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h${minutes % 60}m`;
}

function severityClass(severity) {
  return severity ? severity.toLowerCase() : "p3";
}

export default function IncidentCard({ incident, active, onSelect }) {
  return (
    <div
      className={`incident-card-compact ${active ? "active" : ""}`}
      onClick={() => onSelect(incident.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === "Enter") onSelect(incident.id); }}
    >
      <span className={`badge ${severityClass(incident.severity)}`}>
        {incident.severity || "P3"}
      </span>
      <span className="status-pill">{incident.status}</span>
      <span className="card-title">{incident.title || `Incident: ${incident.component_id}`}</span>
      <span className="card-meta">{incident.component_id}</span>
      <span className="card-meta">⚡ {incident.signal_count}</span>
      <span className="card-meta card-age">{formatAge(incident.created_at)}</span>
    </div>
  );
}
