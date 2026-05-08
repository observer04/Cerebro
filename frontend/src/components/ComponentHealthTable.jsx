import { useEffect, useState, useMemo } from "react";
import { api } from "../api/client";

const COLUMNS = [
  { key: "component_id", label: "Component" },
  { key: "active_incidents", label: "Active" },
  { key: "total_incidents", label: "Total" },
  { key: "avg_mttr_seconds", label: "Avg MTTR" },
  { key: "last_incident", label: "Last Incident" },
];

function formatMttr(seconds) {
  if (!seconds) return "—";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ComponentHealthTable() {
  const [components, setComponents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState("active_incidents");
  const [sortDir, setSortDir] = useState("desc");

  useEffect(() => {
    let mounted = true;
    api
      .getComponentHealth()
      .then((data) => {
        if (mounted) setComponents(data.components || []);
      })
      .catch((err) => console.error("Component health load failed:", err))
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const sorted = useMemo(() => {
    return [...components].sort((a, b) => {
      let av = a[sortKey];
      let bv = b[sortKey];
      if (av == null) av = "";
      if (bv == null) bv = "";
      if (typeof av === "string") {
        return sortDir === "asc"
          ? av.localeCompare(bv)
          : bv.localeCompare(av);
      }
      return sortDir === "asc" ? av - bv : bv - av;
    });
  }, [components, sortKey, sortDir]);

  if (loading) {
    return (
      <div className="health-table-container">
        <div className="empty-state">Loading component health…</div>
      </div>
    );
  }

  if (components.length === 0) {
    return (
      <div className="health-table-container">
        <div className="empty-state">No component data available.</div>
      </div>
    );
  }

  return (
    <div className="health-table-container">
      <div className="health-table-header">
        <span className="section-title">Component Health</span>
      </div>
      <table className="health-table">
        <thead>
          <tr>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                onClick={() => handleSort(col.key)}
              >
                {col.label}
                {sortKey === col.key && (sortDir === "asc" ? " ↑" : " ↓")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((comp) => (
            <tr key={comp.component_id}>
              <td>
                <strong>{comp.component_id}</strong>
              </td>
              <td>
                {comp.active_incidents > 0 ? (
                  <span className="badge p0">{comp.active_incidents}</span>
                ) : (
                  <span style={{ color: "var(--accent-2)" }}>0</span>
                )}
              </td>
              <td>{comp.total_incidents}</td>
              <td>{formatMttr(comp.avg_mttr_seconds)}</td>
              <td>{formatDate(comp.last_incident)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
