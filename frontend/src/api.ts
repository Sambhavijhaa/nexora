import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:5000/api",
  timeout: 10000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("nexora_access_token") || localStorage.getItem("nexora_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing = false;
let queued: Array<(token: string) => void> = [];

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status !== 401 || original?._retry || original?.url?.includes("/auth/")) {
      return Promise.reject(error);
    }

    const refreshToken = localStorage.getItem("nexora_refresh_token");
    if (!refreshToken) {
      localStorage.removeItem("nexora_access_token");
      localStorage.removeItem("nexora_token");
      return Promise.reject(error);
    }

    if (refreshing) {
      return new Promise((resolve) => {
        queued.push((token) => {
          original.headers.Authorization = `Bearer ${token}`;
          resolve(api(original));
        });
      });
    }

    original._retry = true;
    refreshing = true;
    try {
      const { data } = await axios.post(`${api.defaults.baseURL}/auth/refresh`, {}, {
        headers: { Authorization: `Bearer ${refreshToken}` },
      });
      const token = data.accessToken;
      localStorage.setItem("nexora_access_token", token);
      localStorage.setItem("nexora_token", token);
      queued.forEach((resume) => resume(token));
      queued = [];
      original.headers.Authorization = `Bearer ${token}`;
      return api(original);
    } catch (refreshError) {
      queued = [];
      localStorage.removeItem("nexora_access_token");
      localStorage.removeItem("nexora_refresh_token");
      localStorage.removeItem("nexora_token");
      localStorage.removeItem("nexora_user");
      return Promise.reject(refreshError);
    } finally {
      refreshing = false;
    }
  },
);

export default api;
