import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
    scenarios: {
        normal_traffic: {
            executor: 'ramping-arrival-rate',
            startRate: 10,
            timeUnit: '1s',
            preAllocatedVUs: 50,
            maxVUs: 100,
            stages: [
                { target: 20, duration: '30s' },  // Ramp up to normal load
                { target: 20, duration: '1m' },   // Steady normal load
                { target: 5,  duration: '30s' },  // Scale down
            ],
        },
        incident_spike_database: {
            executor: 'constant-arrival-rate',
            rate: 500, // Spike to trigger rate limits/debounce and create an incident
            timeUnit: '1s',
            duration: '30s',
            preAllocatedVUs: 100,
            maxVUs: 500,
            startTime: '45s', // Start this spike 45 seconds into the test
            exec: 'spike_database'
        },
        incident_spike_gateway: {
            executor: 'constant-arrival-rate',
            rate: 600, // Spike to trigger rate limits/debounce and create an incident
            timeUnit: '1s',
            duration: '20s',
            preAllocatedVUs: 100,
            maxVUs: 500,
            startTime: '1m15s', // Start this spike later
            exec: 'spike_gateway'
        }
    },
    thresholds: {
        'checks': ['rate>0.90'],
    },
};

const COMPONENTS = ["api_gateway", "cache", "payment_service", "mcp_host"];

export default function () {
    // Normal traffic randomly distributed across components
    const componentId = COMPONENTS[Math.floor(Math.random() * COMPONENTS.length)];
    const payload = JSON.stringify({
        component_id: componentId,
        source: "k6-normal-traffic",
        metadata: { scenario: "normal_traffic" },
    });
    
    const res = http.post(
        "http://localhost:8000/api/v1/signals",
        payload,
        { headers: { "Content-Type": "application/json" } }
    );

    check(res, {
        "status is 202 or 429": (r) => r.status === 202 || r.status === 429,
    });

    sleep(1); // Prevent a VU from hammering the same component in a tight loop
}

export function spike_database() {
    const payload = JSON.stringify({
        component_id: "database",
        source: "k6-spike-traffic",
        metadata: { scenario: "database_incident", error_code: "CONNECTION_TIMEOUT" },
    });
    
    const res = http.post(
        "http://localhost:8000/api/v1/signals",
        payload,
        { headers: { "Content-Type": "application/json" } }
    );

    check(res, {
        "status is 202 or 429": (r) => r.status === 202 || r.status === 429,
    });
}

export function spike_gateway() {
    const payload = JSON.stringify({
        component_id: "api_gateway",
        source: "k6-spike-traffic",
        metadata: { scenario: "gateway_incident", error_code: "502_BAD_GATEWAY" },
    });
    
    const res = http.post(
        "http://localhost:8000/api/v1/signals",
        payload,
        { headers: { "Content-Type": "application/json" } }
    );

    check(res, {
        "status is 202 or 429": (r) => r.status === 202 || r.status === 429,
    });
}
