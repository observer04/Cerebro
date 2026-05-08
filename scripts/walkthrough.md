# Walkthrough - IMS Demo Scenario Results

I have successfully executed the demo scenario and visualized the results.

## Execution Summary

1. **Started IMS Services**: All containers (Kafka, Redis, MongoDB, Postgres, API, Worker, Frontend) were confirmed running.
2. **Ran k6 Load Test**: Executed `scripts/demo_scenario.js` for 2 minutes.
   - **Normal Traffic**: Simulated baseline load across all components.
   - **Database Spike**: Triggered a high volume of failure signals for the `database` component.
   - **Gateway Spike**: Triggered a high volume of failure signals for the `api_gateway` component.
3. **Generated Visualization**: Used `scripts/visualize_results.py` to create a throughput graph.

## Results Analysis

### Throughput and Status Codes
![IMS Load Test Results](file:///home/observer/projects/ims/load_test_results.png)

- **202 Accepted**: Represents signals that were successfully ingested and queued for processing (including debounced signals).
- **429 Too Many Requests**: Shows the system's rate limiting in action during the peak of the spikes, protecting the ingestion API.

### Incident Ingestion (Database)
Checking the PostgreSQL database confirms that the massive volume of signals (thousands of requests) was correctly deduplicated into a small number of actionable work items:

| Component | Status | Severity | Signal Count |
| --- | --- | --- | --- |
| `database` | OPEN | P0 | 1121 |
| `api_gateway` | OPEN | P1 | 1197 |
| `payment_service` | OPEN | P1 | 351 |

## Conclusion
The system successfully handled the simulated incident spikes by:
1. **Rate Limiting** at the ingestion layer to prevent saturation.
2. **Debouncing/Deduplicating** thousands of signals into single incidents in the database.
3. **Prioritizing** incidents based on component importance (e.g., `database` as P0).
