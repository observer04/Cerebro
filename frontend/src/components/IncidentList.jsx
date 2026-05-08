import { useState, useMemo } from "react";
import IncidentCard from "./IncidentCard";

const SEVERITY_ORDER = { P0: 0, P1: 1, P2: 2, P3: 3 };

const FILTER_PILLS = ["All", "P0", "P1", "P2", "P3"];

const SORT_OPTIONS = [
  { value: "severity", label: "Severity" },
  { value: "newest",   label: "Newest" },
  { value: "signals",  label: "Signal Count" },
];

function normaliseSeverity(s) {
  if (!s) return "P3";
  return s.toUpperCase();
}

export default function IncidentList({ incidents, selectedId, onSelect }) {
  const [filterPill, setFilterPill] = useState("All");
  const [sortKey, setSortKey]       = useState("severity"); // default: severity desc

  const filtered = useMemo(() => {
    let list = filterPill === "All"
      ? incidents
      : incidents.filter(
          (inc) => normaliseSeverity(inc.severity) === filterPill
        );

    list = [...list].sort((a, b) => {
      if (sortKey === "severity") {
        const sa = SEVERITY_ORDER[normaliseSeverity(a.severity)] ?? 99;
        const sb = SEVERITY_ORDER[normaliseSeverity(b.severity)] ?? 99;
        return sa - sb; // P0 first
      }
      if (sortKey === "newest") {
        return new Date(b.created_at) - new Date(a.created_at);
      }
      if (sortKey === "signals") {
        return (b.signal_count ?? 0) - (a.signal_count ?? 0);
      }
      return 0;
    });

    return list;
  }, [incidents, filterPill, sortKey]);

  return (
    <div className="incident-list-wrapper">
      {/* ── Filter + Sort Bar ── */}
      <div className="incident-filter-bar">
        <div className="filter-pills" role="group" aria-label="Filter by severity">
          {FILTER_PILLS.map((pill) => (
            <button
              key={pill}
              id={`filter-pill-${pill.toLowerCase()}`}
              className={`filter-pill ${filterPill === pill ? "active" : ""} ${
                pill !== "All" ? `pill-${pill.toLowerCase()}` : ""
              }`}
              onClick={() => setFilterPill(pill)}
              aria-pressed={filterPill === pill}
            >
              {pill}
            </button>
          ))}
        </div>

        <div className="sort-group">
          <label htmlFor="incident-sort" className="sort-label">Sort</label>
          <select
            id="incident-sort"
            className="sort-select"
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value)}
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Incident Cards ── */}
      {filtered.length === 0 ? (
        <div className="empty-state">
          {incidents.length === 0
            ? "No active incidents."
            : `No ${filterPill} incidents.`}
        </div>
      ) : (
        <div className="incident-list">
          {filtered.map((incident) => (
            <IncidentCard
              key={incident.id}
              incident={incident}
              active={incident.id === selectedId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}
