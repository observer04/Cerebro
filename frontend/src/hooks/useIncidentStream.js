import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../api/client";

const EMPTY_METRICS = {
  signalsPerSecond: 0,
  activeIncidents: 0,
  avgMttrSeconds: 0
};

export function useIncidentStream() {
  const [incidents, setIncidents] = useState([]);
  const [metrics, setMetrics] = useState(EMPTY_METRICS);
  const [connected, setConnected] = useState(false);
  const refreshTimer = useRef(null);
  const mttrSamples = useRef([]);

  const refreshIncidents = useCallback(async () => {
    try {
      const data = await api.getDashboardActive();
      setIncidents(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn("Failed to refresh incidents", err);
    }
  }, []);

  const scheduleRefresh = useCallback(() => {
    if (refreshTimer.current) {
      return;
    }
    refreshTimer.current = window.setTimeout(() => {
      refreshTimer.current = null;
      refreshIncidents();
    }, 350);
  }, [refreshIncidents]);

  useEffect(() => {
    refreshIncidents();
  }, [refreshIncidents]);

  useEffect(() => {
    setMetrics((prev) => ({
      ...prev,
      activeIncidents: incidents.length
    }));
  }, [incidents]);

  useEffect(() => {
    const source = new EventSource("/api/v1/stream/events");
    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);

    source.onmessage = (event) => {
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch (_err) {
        return;
      }

      if (!payload || !payload.type) {
        return;
      }

      if (payload.type.startsWith("incident.")) {
        scheduleRefresh();
      }

      if (payload.type === "metrics.throughput") {
        const value = payload.data?.signals_per_second;
        if (typeof value === "number") {
          setMetrics((prev) => ({ ...prev, signalsPerSecond: value }));
        }
      }

      if (payload.type === "incident.closed") {
        const mttr = payload.data?.mttr_seconds;
        if (typeof mttr === "number") {
          mttrSamples.current.unshift(mttr);
          mttrSamples.current = mttrSamples.current.slice(0, 20);
          const sum = mttrSamples.current.reduce((acc, item) => acc + item, 0);
          setMetrics((prev) => ({
            ...prev,
            avgMttrSeconds: sum / mttrSamples.current.length
          }));
        }
      }
    };

    return () => {
      source.close();
    };
  }, [scheduleRefresh]);

  const updateIncident = useCallback((id, patch) => {
    setIncidents((prev) =>
      prev.map((item) => (item.id === id ? { ...item, ...patch } : item))
    );
  }, []);

  return {
    incidents,
    metrics,
    connected,
    refreshIncidents,
    updateIncident
  };
}
