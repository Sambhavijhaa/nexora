import axios, { type AxiosRequestConfig } from "axios";

// Explicit production API URL. This prevents a stale Vercel environment
// variable from sending login requests to an old backend.
const API_BASE_URL = "https://nexora-backend-7i97.onrender.com/api";
const API_TIMEOUT = 60000;

type RetryableConfig = AxiosRequestConfig & { _retry?: boolean };

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("nexora_access_token") || localStorage.getItem("nexora_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing = false;
let queued: Array<(token: string) => void> = [];

api.interceptors.response.use((response) => response, async (error) => {
  const original = error.config as RetryableConfig | undefined;
  if (error.response?.status !== 401 || !original || original._retry || original.url?.includes("/auth/")) {
    return Promise.reject(error);
  }
  const refreshToken = localStorage.getItem("nexora_refresh_token");
  if (!refreshToken) return Promise.reject(error);
  if (refreshing) {
    return new Promise((resolve) => queued.push((token) => {
      original.headers = original.headers ?? {};
      original.headers.Authorization = `Bearer ${token}`;
      resolve(api(original));
    }));
  }
  original._retry = true;
  refreshing = true;
  try {
    const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, {}, {
      headers: { Authorization: `Bearer ${refreshToken}`, "Content-Type": "application/json" },
      timeout: API_TIMEOUT,
    });
    const token = data.accessToken;
    if (!token) throw new Error("Refresh endpoint returned no access token.");
    localStorage.setItem("nexora_access_token", token);
    localStorage.setItem("nexora_token", token);
    queued.forEach((resume) => resume(token));
    queued = [];
    original.headers = original.headers ?? {};
    original.headers.Authorization = `Bearer ${token}`;
    return api(original);
  } catch (refreshError) {
    queued = [];
    ["nexora_access_token", "nexora_refresh_token", "nexora_token", "nexora_user"].forEach((key) => localStorage.removeItem(key));
    return Promise.reject(refreshError);
  } finally {
    refreshing = false;
  }
});

export default api;
