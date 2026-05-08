import { useEffect, useState } from "react";

import { api } from "../api/client";
import ComponentHealthTable from "../components/ComponentHealthTable";
import Header from "../components/Header";
import IncidentDetail from "../components/IncidentDetail";
import IncidentList from "../components/IncidentList";
import MetricsBar from "../components/MetricsBar";
import SystemHealthBar from "../components/SystemHealthBar";

export default function DashboardPage({ stream }) {
  const { incidents, metrics, connected, refreshIncidents, updateIncident } = stream;
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!incidents.length) {
      if (selectedId) {
        setSelectedId(null);
      }
      return;
    }

    const exists = incidents.some((item) => item.id === selectedId);
    if (!selectedId || !exists) {
      setSelectedId(incidents[0].id);
    }
  }, [incidents, selectedId]);

  const selectedIncident = incidents.find((item) => item.id === selectedId) || null;

  const handleTransition = async (target) => {
    if (!selectedIncident) {
      return;
    }
    setError("");
    try {
      const payload = await api.transitionWorkItem(selectedIncident.id, {
        target_status: target,
        assignee: selectedIncident.assignee || "oncall@corp.com"
      });
      updateIncident(selectedIncident.id, { status: payload.status });
      await refreshIncidents();
    } catch (err) {
      setError(err.message || "Transition failed");
    }
  };

  const handleRcaSubmitted = async (rca) => {
    if (!selectedIncident) {
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.submitRca(selectedIncident.id, rca);
      await refreshIncidents();
    } catch (err) {
      setError(err.message || "RCA submission failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Header connected={connected} />
      <main className="page">
        <SystemHealthBar />
        <MetricsBar metrics={metrics} />
        <div className="grid">
          <IncidentList
            incidents={incidents}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
          <IncidentDetail
            incident={selectedIncident}
            onTransition={handleTransition}
            onRcaSubmitted={handleRcaSubmitted}
            busy={busy}
            error={error}
          />
        </div>
        <ComponentHealthTable />
      </main>
    </>
  );
}

