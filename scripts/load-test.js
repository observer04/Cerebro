import http from "k6/http";
import { check } from "k6";

// export const options = {
//   stages: [
//     { duration: "30s", target: 5000 },
//     { duration: "1m", target: 10000 },
//     { duration: "30s", target: 0 },
//   ],
//   thresholds: {
//     checks: ["rate>0.95"],
//   },
// };

export const options = {
    scenarios: {
        signal_burst: {
            executor: 'constant-arrival-rate',
            rate: 2000,           // 2000 requests/sec
            timeUnit: '1s',
            duration: '2m',
            preAllocatedVUs: 500,
            maxVUs: 1000,         // never more than 1000 open connections
        },
    },
    thresholds: {
        'checks': ['rate>0.95'],
        'http_req_failed': ['rate<0.05'],
    },
};

const COMPONENTS = ["database", "api_gateway", "cache", "payment_service", "mcp_host"];

export default function () {
  const componentId = COMPONENTS[Math.floor(Math.random() * COMPONENTS.length)];
  const payload = JSON.stringify({
    component_id: componentId,
    source: "k6-load-test",
    metadata: { test: true },
  });
  const res = http.post(
    "http://localhost:8000/api/v1/signals",
    payload,
    { headers: { "Content-Type": "application/json" } }
  );

  check(res, {
    "status is 202 or 429": (r) => r.status === 202 || r.status === 429,
    "no 500 errors": (r) => r.status !== 500,
  });
}

export function teardown() {
  const health = http.get("http://localhost:8000/health");
  check(health, {
    "health returns 200": (r) => r.status === 200,
    "throughput metric exists": (r) => {
      const body = JSON.parse(r.body);
      return body.throughput && body.throughput.signals_per_second !== undefined;
    },
  });
}
