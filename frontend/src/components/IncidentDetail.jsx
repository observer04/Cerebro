import IncidentTimeline from "./IncidentTimeline";
import RCAForm from "./RCAForm";
import SignalDrawer from "./SignalDrawer";
import StateTransitionPanel from "./StateTransitionPanel";

export default function IncidentDetail({ incident, onTransition, onRcaSubmitted, busy, error }) {
  if (!incident) {
    return (
      <div className="detail-panel">
        <div className="empty-state">Select an incident to inspect details.</div>
      </div>
    );
  }

  return (
    <div className="detail-panel">
      <div className="section">
        <div className="section-title">Incident Detail</div>
        <h2>{incident.title || `Incident: ${incident.component_id}`}</h2>
        <div className="incident-meta">
          <span>Component: {incident.component_id}</span>
          <span>Status: {incident.status}</span>
          <span>Signals: {incident.signal_count}</span>
        </div>
        {error ? <div className="helper">{error}</div> : null}
      </div>

      <div className="section">
        <div className="section-title">Transitions</div>
        <StateTransitionPanel
          incident={incident}
          onTransition={onTransition}
        />
      </div>

      <SignalDrawer workItemId={incident.id} />

      <IncidentTimeline workItemId={incident.id} />

      {incident.status === "RESOLVED" ? (
        <RCAForm onSubmit={onRcaSubmitted} busy={busy} />
      ) : null}
    </div>
  );
}

