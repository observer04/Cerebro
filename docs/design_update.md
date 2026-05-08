# IMS — Design Update: Data Store Surface Features

## Problem Statement

The IMS architecture uses three distinct data stores — **Redis**, **MongoDB**, and **PostgreSQL/TimescaleDB** — each with clear single-responsibility roles. However, the current frontend **never reads from any of them directly**:

| Data Store | Current Write Path | Current Read Path (UI) |
|---|---|---|
| **Redis** | Debounce keys, dashboard cache, throughput counter, pub/sub | ❌ SSE events only (pub/sub) — no cache reads |
| **MongoDB** | Raw signal `insert_one` per signal | ❌ Never queried — dead data lake |
| **PostgreSQL** | Work items, RCA records | ✅ Work item list + transitions only |
| **TimescaleDB** | `metrics` hypertable (signals/sec) | ⚠️ Basic metric list only — no time-series aggregation |

The assignment explicitly requires:
> **Incident Detail:** Click an incident to see the raw signals **(from NoSQL)** and the current status.

This is currently missing, along with several features that would demonstrate mastery of the polyglot persistence architecture.

---

## Proposed Features

### Feature 1 — Raw Signal Inspector (MongoDB)

**Assignment requirement.** When a user clicks an incident, the detail panel should show the raw signals that were debounced into that work item.

#### Backend

**New endpoint:** `GET /api/v1/work-items/{work_item_id}/signals`

```
Query: MongoDB raw_signals collection
Filter: { component_id: work_item.component_id, 
          timestamp: { $gte: work_item.created_at - 10s,
                       $lte: work_item.resolved_at || now() } }
Sort:   { timestamp: -1 }
Limit:  100
```

**Response shape:**
```json
{
  "signals": [
    {
      "signal_id": "uuid",
      "component_id": "CACHE_CLUSTER_01",
      "source": "monitoring-agent",
      "severity_hint": "critical",
      "timestamp": "2026-05-08T10:00:01Z",
      "metadata": { "error": "connection_timeout", "latency_ms": 4200 }
    }
  ],
  "total": 87,
  "showing": 100
}
```

**Why this matters:** This is the audit trail. Raw signals carry heterogeneous `metadata` payloads (latency numbers, error codes, stack traces) that the structured work item doesn't capture. Seeing these lets an engineer understand *what actually happened*, not just that something happened.

#### Frontend

New `SignalDrawer` component in the incident detail panel:
- Collapsible section titled "Raw Signals (87)" below the incident metadata
- Each signal rendered as a compact card showing: timestamp, source, severity_hint
- Expandable JSON viewer for the `metadata` field (the raw error payload)
- Signals are lazy-loaded on first expand (not fetched until the user clicks)

---

### Feature 2 — System Health Dashboard (Redis)

Expose the Redis-cached operational state that the backend already maintains but the frontend never reads.

#### Backend

**New endpoint:** `GET /api/v1/system/health-summary`

This endpoint aggregates data the system already tracks in Redis:
- `dashboard:active_incidents` sorted set → incident count by severity
- `metrics:signals_rate` → current throughput
- `debounce:*` key scan (COUNT only) → active debounce windows
- Connection status to all 3 stores (already in `/health`)

```json
{
  "throughput": { "signals_per_second": 142.5 },
  "debounce": { "active_windows": 3 },
  "incidents": { "total": 12, "by_severity": { "P0": 1, "P1": 3, "P2": 5, "P3": 3 } },
  "stores": {
    "redis": "healthy",
    "mongodb": "healthy",
    "postgres": "healthy",
    "kafka": "healthy"
  }
}
```

**Performance note:** This reads exclusively from Redis (O(1) reads + one `SCAN`). Zero PostgreSQL queries. Demonstrates the "hot-path cache" role described in the architecture.

#### Frontend

New `SystemHealthBar` component replacing the current minimal `MetricsBar`:
- Animated severity breakdown (colored dots: 🔴 P0, 🟠 P1, 🟡 P2, 🔵 P3)
- Live throughput gauge
- Active debounce windows count (shows the system is actively deduplicating)
- Store health indicators (green/red dots for each backing store)
- Auto-refreshes via SSE events + 10s polling fallback

---

### Feature 3 — Incident Timeline (PostgreSQL + MongoDB)

A chronological timeline view combining structured state transitions (PostgreSQL) with raw signal bursts (MongoDB) into a single visual narrative.

#### Backend

**New endpoint:** `GET /api/v1/work-items/{work_item_id}/timeline`

Merges two data sources into a unified timeline:

1. **PostgreSQL** — State transitions (created_at, status changes, resolved_at, RCA submission)
2. **MongoDB** — Raw signal bursts aggregated into time buckets

```json
{
  "timeline": [
    { "time": "T0", "type": "incident.created", "detail": "Opened as P0" },
    { "time": "T0-T10s", "type": "signal.burst", "count": 47, "sources": ["monitor-1", "monitor-2"] },
    { "time": "T+2m", "type": "transition", "from": "OPEN", "to": "INVESTIGATING", "actor": "oncall@corp.com" },
    { "time": "T+10s-T+20s", "type": "signal.burst", "count": 23, "sources": ["monitor-1"] },
    { "time": "T+15m", "type": "transition", "from": "INVESTIGATING", "to": "RESOLVED" },
    { "time": "T+20m", "type": "rca.submitted", "submitted_by": "oncall@corp.com" },
    { "time": "T+20m", "type": "incident.closed", "mttr_seconds": 1200 }
  ]
}
```

**Data source mapping:**
- Signal bursts → MongoDB `raw_signals` aggregated with `$group` by 10-second windows
- Transitions → PostgreSQL `work_items` (created_at, updated_at, resolved_at) + `rca_records` (submitted_at)

#### Frontend

New `IncidentTimeline` component in the detail panel:
- Vertical timeline with icons for each event type
- Signal bursts shown as bar segments (wider = more signals)
- State transitions shown as labeled nodes
- RCA submission shown as a document icon
- MTTR shown as a duration label spanning the full timeline

---

### Feature 4 — Time-Series Analytics Page (TimescaleDB)

Replace the current basic metrics list with proper time-series visualization leveraging TimescaleDB's `time_bucket` function — the whole reason TimescaleDB exists in this stack.

#### Backend

**New endpoint:** `GET /api/v1/analytics/throughput`

Uses TimescaleDB's native `time_bucket` for server-side aggregation:
```sql
SELECT 
  time_bucket('1 minute', time) AS bucket,
  metric_name,
  AVG(value) AS avg_value,
  MAX(value) AS max_value,
  MIN(value) AS min_value
FROM metrics
WHERE time > NOW() - INTERVAL '1 hour'
  AND metric_name = $1
GROUP BY bucket, metric_name
ORDER BY bucket DESC;
```

**Query parameters:**
- `metric_name` — filter (e.g., `signals_per_second`, `active_incidents`)
- `interval` — bucket size (`1m`, `5m`, `15m`, `1h`)
- `range` — lookback window (`1h`, `6h`, `24h`)

**Response:**
```json
{
  "metric_name": "signals_per_second",
  "interval": "1m",
  "range": "1h",
  "buckets": [
    { "time": "2026-05-08T10:00:00Z", "avg": 142.5, "max": 312.0, "min": 45.2 },
    { "time": "2026-05-08T10:01:00Z", "avg": 156.3, "max": 289.1, "min": 67.8 }
  ]
}
```

**Why this matters:** The current metrics endpoint returns raw rows. TimescaleDB's `time_bucket` is purpose-built for this — it's the reason the design document chose TimescaleDB over plain PostgreSQL for the metrics table.

#### Frontend

Rewrite `MetricsPage` with:
- Time-range selector (1h / 6h / 24h buttons)
- Interval selector (1m / 5m / 15m)
- Proper area chart with avg/min/max bands (rendered with canvas or SVG — no charting library needed for simple area charts)
- Auto-refreshes every 10 seconds

---

### Feature 5 — Component Heatmap (Cross-Store)

A bird's-eye view showing which infrastructure components are failing the most. Combines all 3 stores.

#### Backend

**New endpoint:** `GET /api/v1/analytics/component-health`

Aggregates across stores:
1. **PostgreSQL** — Active incidents per component, avg MTTR per component
2. **MongoDB** — Signal count per component in last hour
3. **Redis** — Currently active debounce windows per component

```json
{
  "components": [
    {
      "component_id": "CACHE_CLUSTER_01",
      "active_incidents": 2,
      "signals_last_hour": 847,
      "avg_mttr_seconds": 1200,
      "is_debouncing": true,
      "severity": "P2"
    },
    {
      "component_id": "RDBMS_PRIMARY",
      "active_incidents": 1,
      "signals_last_hour": 3200,
      "avg_mttr_seconds": null,
      "is_debouncing": true,
      "severity": "P0"
    }
  ]
}
```

#### Frontend

New `ComponentHealth` component on the dashboard:
- Grid of component tiles, colored by health status (green → yellow → red based on signal volume + severity)
- Each tile shows: component name, signal rate, active incident count
- Pulsing animation on tiles with active debounce windows (shows the system is actively processing bursts)
- Click a component to filter the incident list to that component

---

## New Routes Summary

| Method | Endpoint | Data Store | Purpose |
|--------|----------|------------|---------|
| GET | `/api/v1/work-items/{id}/signals` | MongoDB | Raw signal audit trail |
| GET | `/api/v1/system/health-summary` | Redis | Cached operational state |
| GET | `/api/v1/work-items/{id}/timeline` | PostgreSQL + MongoDB | Unified incident chronology |
| GET | `/api/v1/analytics/throughput` | TimescaleDB | Time-bucketed metric aggregation |
| GET | `/api/v1/analytics/component-health` | All 3 | Cross-store component overview |

## New Frontend Routes

| Path | Page | Key Component |
|------|------|---------------|
| `/` | Dashboard (enhanced) | `SystemHealthBar`, `ComponentHealth`, `IncidentTimeline`, `SignalDrawer` |
| `/metrics` | Analytics (rewritten) | Time-series chart with `time_bucket` data |

## Implementation Order

Features are ordered by assignment-impact, not effort:

1. **Feature 1 — Raw Signal Inspector** ← **mandatory assignment requirement**, directly addresses the "Incident Detail: click to see raw signals from NoSQL" criterion
2. **Feature 4 — Time-Series Analytics** ← demonstrates TimescaleDB purpose, justifies tech stack choice
3. **Feature 2 — System Health Dashboard** ← demonstrates Redis as hot-path cache (not just pub/sub)
4. **Feature 3 — Incident Timeline** ← demonstrates cross-store data join, impressive UX
5. **Feature 5 — Component Heatmap** ← the differentiator, shows architectural mastery

## Design Constraints

- All new endpoints are **read-only** (GET). No schema changes to existing tables.
- MongoDB queries use existing `{ component_id, timestamp }` index.
- Redis reads are O(1) or bounded SCAN. No unbounded key iteration.
- TimescaleDB uses native `time_bucket` — no client-side aggregation.
- Frontend components are lazy-loaded (signals fetched on click, not on page load).
- No new npm dependencies. Charts rendered with SVG/canvas.
- All feature additions are backward-compatible. Existing pages continue working.
