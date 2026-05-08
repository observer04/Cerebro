const API_ROOT = "/api/v1";

function buildQuery(params = {}) {
  const entries = Object.entries(params).filter(([, value]) => value !== undefined && value !== null);
  if (!entries.length) {
    return "";
  }
  const search = new URLSearchParams();
  for (const [key, value] of entries) {
    search.set(key, String(value));
  }
  return `?${search.toString()}`;
}

async function request(path, options = {}) {
  const config = {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  };

  if (config.body && typeof config.body !== "string") {
    config.body = JSON.stringify(config.body);
  }

  const response = await fetch(`${API_ROOT}${path}`, config);
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (_err) {
      data = null;
    }
  }

  if (!response.ok) {
    const detail = data && data.detail ? JSON.stringify(data.detail) : response.statusText;
    throw new Error(detail);
  }

  return data;
}

export const api = {
  listWorkItems: (params) => request(`/work-items${buildQuery(params)}`),
  getWorkItem: (id) => request(`/work-items/${id}`),
  transitionWorkItem: (id, payload) =>
    request(`/work-items/${id}/transition`, { method: "PATCH", body: payload }),
  submitRca: (id, payload) =>
    request(`/work-items/${id}/rca`, { method: "POST", body: payload }),
  getDashboardActive: () => request(`/dashboard/active`),
  getDashboardMetrics: () => request(`/dashboard/metrics`)
};
