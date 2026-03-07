import { getToken, clearAuth } from "./auth";

// In Docker, nginx proxies /api → backend:8000. In local dev (vite proxy), same applies.
const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";

async function fetchAPI(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (resp.status === 401) {
    clearAuth();
    window.location.reload();
    return;
  }

  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(error.detail || "Request failed");
  }
  return resp.json();
}

export const api = {
  // Auth
  register: (data) => fetchAPI("/auth/register", { method: "POST", body: JSON.stringify(data) }),
  login: (data) => fetchAPI("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  googleAuth: (id_token) => fetchAPI("/auth/google", { method: "POST", body: JSON.stringify({ id_token }) }),
  getMe: () => fetchAPI("/auth/me"),

  // Admin
  adminStats: () => fetchAPI("/admin/stats"),
  adminListUsers: (skip = 0, limit = 50) => fetchAPI(`/admin/users?skip=${skip}&limit=${limit}`),
  adminCreateUser: (data) => fetchAPI("/admin/users", { method: "POST", body: JSON.stringify(data) }),
  adminUpdateUser: (id, data) => fetchAPI(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  adminDeleteUser: (id) => fetchAPI(`/admin/users/${id}`, { method: "DELETE" }),
  adminListScans: (skip = 0, limit = 50) => fetchAPI(`/admin/scans?skip=${skip}&limit=${limit}`),
  adminDeleteScan: (id) => fetchAPI(`/admin/scans/${id}`, { method: "DELETE" }),

  // Scans
  createScan: (data) => fetchAPI("/scans/", { method: "POST", body: JSON.stringify(data) }),
  listScans: (skip = 0, limit = 20) => fetchAPI(`/scans/?skip=${skip}&limit=${limit}`),
  getScan: (id) => fetchAPI(`/scans/${id}`),
  deleteScan: (id) => fetchAPI(`/scans/${id}`, { method: "DELETE" }),
  getScanProgress: (id) => fetchAPI(`/scans/${id}/progress`),

  // Findings
  getScanFindings: (scanId, filters = {}) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => v && params.set(k, v));
    return fetchAPI(`/results/scan/${scanId}?${params.toString()}`);
  },
  getScanStats: (scanId) => fetchAPI(`/results/scan/${scanId}/stats`),

  // Settings
  getSettings: () => fetchAPI("/settings/"),
  updateSettings: (data) => fetchAPI("/settings/", { method: "POST", body: JSON.stringify(data) }),

  // Health
  health: () => fetchAPI("/health"),
};

export const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];

export const SEVERITY_COLORS = {
  critical: "var(--severity-critical)",
  high: "var(--severity-high)",
  medium: "var(--severity-medium)",
  low: "var(--severity-low)",
  info: "var(--severity-info)",
};

export const CATEGORY_LABELS = {
  sensitive_files: "Sensitive Files",
  admin_panels: "Admin Panels",
  directory_listings: "Directory Listings",
  backup_files: "Backup Files",
  config_files: "Config Files",
  credentials: "Credentials",
  documents: "Documents",
  database_dumps: "Database Dumps",
  cloud_storage: "Cloud Storage",
  github_leaks: "GitHub Leaks",
  api_endpoints: "API Endpoints",
  other: "Other",
};

export const SOURCE_LABELS = {
  google: "Google",
  bing: "Bing",
  duckduckgo: "DuckDuckGo",
  yandex: "Yandex",
  github: "GitHub",
  cloud_scan: "Cloud Scan",
};

export function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export function truncateUrl(url, maxLen = 60) {
  if (!url) return "";
  if (url.length <= maxLen) return url;
  return url.substring(0, maxLen) + "...";
}
