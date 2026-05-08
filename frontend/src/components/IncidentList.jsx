import IncidentCard from "./IncidentCard";

export default function IncidentList({ incidents, selectedId, onSelect }) {
  if (!incidents.length) {
    return <div className="empty-state">No active incidents.</div>;
  }

  return (
    <div className="incident-list">
      {incidents.map((incident) => (
        <IncidentCard
          key={incident.id}
          incident={incident}
          active={incident.id === selectedId}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}
