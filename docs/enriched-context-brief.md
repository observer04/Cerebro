# Enriched Context Brief: Mission-Critical Incident Management System (IMS)

## Design Phase

---

## 1. Who You Are in This Context

You are the **lead architect** on a backend engineering challenge. Your job in this phase is to produce `design.md` - a comprehensive architectural design document that reflects senior-level decision making. Every choice you make must be **explicitly justified** against the scoring rubric and the system's constraints. No hand-waving. No "this is industry standard" without explaining why it fits this system.

---

## 2. What Is Being Built (Plain English)

A production-grade **Incident Management System (IMS)** that does five things:

1. **Ingests** high-volume error signals from a distributed infrastructure (APIs, caches, queues, databases). Think: 10,000 signals/second arriving in bursts.
2. **Deduplicates** those signals - if 100 signals arrive for the same broken component within 10 seconds, only ONE work item (ticket) is created. All 100 signals are stored and linked to it.
3. **Routes and alerts** the right responders based on component severity - a database failure wakes someone up (P0), a cache failure sends a Slack message (P2).
4. **Tracks the incident lifecycle** from OPEN → INVESTIGATING → RESOLVED → CLOSED, with mandatory Root Cause Analysis (RCA) before closure.
5. **Displays everything** on a live dashboard with a React frontend that engineers can use to investigate and close incidents.

---

## 3. Non-Negotiable Constraints

These are hard requirements. Opus must design around them, not ignore them:

- **The system cannot crash if the persistence layer is slow.** Backpressure must be handled explicitly. Signals must be buffered durably.
- **State transitions must be transactional.** You cannot have a race condition where a work item is simultaneously transitioned by two consumers.
- **RCA is mandatory for CLOSED state.** Any attempt to transition to CLOSED without a complete RCA object must be rejected at the application layer - not just in the UI.
- **MTTR must be calculated automatically** from `start_time` (first signal timestamp) to `end_time` (RCA submission timestamp).
- **The debounce window is exactly 10 seconds per component_id.** This must be enforced with precision.
- **All code is async.** No synchronous blocking calls anywhere in the hot path.
- **A `/health` endpoint must exist.** Throughput metrics (signals/sec) must be logged to console every 5 seconds.
- **Rate limiting on the ingestion API** is mandatory to prevent the IMS itself from becoming a failure point.

---

## 4. The Scoring Rubric (What Opus Must Optimize For)

This is an evaluated engineering challenge. Here is exactly what each category rewards:

| Category                   | Weight | What Actually Scores Marks                                                                                                                                       |
| -------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Data Handling**          | 20%    | Strict separation: each data store has ONE purpose and ONE type of data. Justified choice of store per data type. No "just use MongoDB for everything."          |
| **LLD (Low-Level Design)** | 20%    | Correct, textbook-accurate use of Strategy Pattern and State Pattern. Not just "I used classes." The patterns must be architecturally necessary, not decorative. |
| **UI/UX & Integration**    | 20%    | A live feed that is actually live (not polling every 5s). React frontend with correct API integration. RCA form that enforces validation before submission.      |
| **Resilience & Testing**   | 10%    | Explicit retry logic with exponential backoff on DB writes. Unit tests specifically for RCA validation logic. Evidence of thinking about failure modes.          |
| **Documentation**          | 10%    | Architecture diagram (Mermaid is acceptable). README with backpressure section. This spec/design document itself checked into the repo earns marks.              |
| **Tech Stack Choices**     | 10%    | Justified decisions, not just popular choices. The evaluator wants to see _why_ each tool was chosen over alternatives.                                          |
| **Concurrency & Scaling**  | 10%    | No race conditions during concurrent state updates. Proper async primitives. Demonstrate the system handles burst traffic without data loss.                     |

---

## 5. Agreed Architecture Decisions (Non-Negotiable Starting Points)

### Language & Framework

- **Backend: Python with FastAPI** (async-first, pattern-friendly, evaluator-readable)
- **Frontend: React** with a genuinely live feed - not polling

### The Five Data Stores (Each Has Exactly One Job)

| Store           | Its Single Responsibility                                                                                                                     |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **Kafka**       | The durable bridge between signal ingestion and processing. Signals are never lost here even if every downstream store is slow or down.       |
| **Redis**       | Anything that needs to be read instantly and can tolerate being rebuilt. The debounce window state and the dashboard hot-path both live here. |
| **MongoDB**     | Every raw signal ever received, exactly as it arrived. The append-only audit trail.                                                           |
| **PostgreSQL**  | Work Items and RCA records. The only store where transactional correctness matters.                                                           |
| **TimescaleDB** | Timeseries metrics. This is a PostgreSQL extension - not a separate service.                                                                  |

### Three Features That Must Be Designed With Care

**Debouncing:** Within any 10-second window, 100 signals about the same broken component must produce exactly one Work Item - not 100. All 100 signals must still be stored and linked. The design must ensure this is race-condition safe even under concurrent load. Opus should reason carefully about where in the pipeline this check happens and what mechanism guarantees atomicity.

**Backpressure:** The system must stay alive even when the database is slow or temporarily unreachable. Signals in flight cannot be silently dropped. Opus should design an explicit chain of what happens when each layer gets overwhelmed from the ingestion API all the way down to persistence - and where the system applies back-pressure versus where it rejects gracefully.

**Alerting and Incident Lifecycle:** Different component failures have different severity and require different notification behavior. The design must make it trivially easy to add a new component type with new alerting behavior without touching existing logic. Similarly, the incident lifecycle (OPEN → INVESTIGATING → RESOLVED → CLOSED) must enforce its own rules - invalid transitions should be impossible, and the CLOSED state must be unreachable without a complete RCA. Opus should choose the right software design patterns for each of these two problems and justify why.

---

## 6. What design.md Must Achieve

The document should be something a senior engineer could hand to a development team and have them build the system without asking clarifying questions. That's the bar.

At minimum, anyone reading it should walk away knowing:

- **What every service and data store does** - and why that store was chosen over the obvious alternative
- **How a signal travels end-to-end** - from the moment it hits the ingestion API to the moment it appears on the dashboard, with every handoff explained
- **How the system stays alive under stress** - the complete backpressure and failure chain, not just "Kafka handles it"
- **How the incident lifecycle is enforced** - including what makes invalid transitions impossible and what gates the CLOSED state
- **How alerting works across different component types** - and how a new component type would be added by a new engineer with zero changes to existing code
- **What every API endpoint does** - enough detail that a frontend engineer could build against it without a meeting
- **How the frontend stays live** - the real-time data flow from backend event to UI update
- **How MTTR is calculated** - when, where, and stored or derived

An architecture diagram is expected. Pseudocode for the two or three most critical algorithms (debounce, state transition enforcement) is encouraged but not required. Implementation code is not.

---

## 7. What design.md Must NOT Do

- Do not write implementation code. Pseudocode for critical algorithms (debounce, state transitions) is acceptable and encouraged.
- Do not leave any decision as "TBD" or "to be determined later."
- Do not say "we will use X" without explaining why X over Y.
- Do not use the State Pattern for alerting or the Strategy Pattern for state management. These are distinct problems requiring distinct patterns.
- Do not make TimescaleDB a separate Docker service. It is a PostgreSQL extension.
- Do not use polling for the live dashboard. SSE or WebSockets only.
- Do not allow the CLOSED transition without RCA validation in the state object itself.
- Do not hit the max output token limit and stay within it.

---

## 8. Quality Bar

The design.md document, when complete, should be something a senior engineer at a product company would be comfortable handing to a team to implement. It should answer the question "why did you make this choice?" for every non-obvious decision. The evaluator will read this document and it directly scores marks in Documentation (10%) and Tech Stack Choices (10%), and validates LLD (20%).

When you are done with design.md, stop. Do not begin implementation. The implementation-plan.md will be a separate phase after design review.

---

## 9. Submission Context

- Repository structure: `/backend` and `/frontend`
- Docker Compose is mandatory for setup
- A `scripts/seed_failure_event.py` (or `.json`) must be included to simulate: RDBMS outage → MCP failure cascade
- This spec document will be checked into the repo as `docs/enriched-context-brief.md`
- Submission deadline: 1 week from receipt

---
