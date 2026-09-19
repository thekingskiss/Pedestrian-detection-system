/**
 * Thin fetch wrapper. Talks to the FastAPI backend defined in
 * ../backend/app/api/v1/router.py — every path here corresponds 1:1 to a
 * router mounted there.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";
export const WS_BASE = import.meta.env.VITE_WS_BASE_URL || "ws://localhost:8000/api/v1/ws";

function getToken() {
  return localStorage.getItem("pds_token");
}

export function setToken(token) {
  if (token) localStorage.setItem("pds_token", token);
  else localStorage.removeItem("pds_token");
}

async function request(path, { method = "GET", body, form, file } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let payload = body;
  if (file) {
    payload = file; // FormData — browser sets the multipart Content-Type + boundary itself
  } else if (form) {
    payload = new URLSearchParams(form);
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (body) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(`${API_BASE}${path}`, { method, headers, body: payload });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  login: (email, password) => request("/auth/login", { method: "POST", form: { username: email, password } }),

  register: (email, password) => request("/auth/register", { method: "POST", body: { email, password } }),

  me: () => request("/auth/me"),

  dashboardSummary: (hours = 24) => request(`/dashboard/summary?hours=${hours}`),

  listCameras: () => request("/cameras/"),
  createCamera: (payload) => request("/cameras/", { method: "POST", body: payload }),
  uploadCameraVideo: (cameraId, formData) => request(`/cameras/${cameraId}/video`, { method: "POST", file: formData }),
  listZones: (cameraId) => request(`/zones/${cameraId ? `?camera_id=${cameraId}` : ""}`),
  createZone: (payload) => request("/zones/", { method: "POST", body: payload }),

  listDetections: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/detections/${qs ? `?${qs}` : ""}`);
  },

  listAlerts: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/alerts/${qs ? `?${qs}` : ""}`);
  },
  acknowledgeAlert: (id) =>
    request(`/alerts/${id}/acknowledge`, { method: "PATCH", body: { acknowledged: true } }),

  listUsers: () => request("/users/"),
  createUser: (payload) => request("/users/", { method: "POST", body: payload }),
  deactivateUser: (id) => request(`/users/${id}`, { method: "DELETE" }),

  listModelVersions: () => request("/models/"),
  activateModelVersion: (id) => request(`/models/${id}/activate`, { method: "POST" }),
};