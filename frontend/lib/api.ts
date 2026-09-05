import axios from "axios";

export const getApiBaseUrl = (): string => {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (
    typeof window !== "undefined" &&
    (window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1")
  ) {
    return "http://localhost:8000";
  }
  return "https://enav-backend.onrender.com";
};

export const api = axios.create({
  baseURL: getApiBaseUrl(),
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor to attach auth token & dynamic baseURL
api.interceptors.request.use(
  (config) => {
    config.baseURL = getApiBaseUrl();
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error and 401/403 handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && (error.response.status === 401 || error.response.status === 403)) {
      if (typeof window !== "undefined") {
        const currentPath = window.location.pathname || "";
        const requestUrl = error.config?.url || "";
        const isAuthRequest = requestUrl.includes("/auth/login") || requestUrl.includes("/auth/register");
        const isAuthPage = currentPath.includes("/auth/login") || currentPath.includes("/auth/signup");

        // Only redirect to login if the user is on a protected dashboard and the session expired
        if (!isAuthRequest && !isAuthPage) {
          localStorage.removeItem("token");
          window.location.href = "/auth/login";
        }
      }
    }
    return Promise.reject(error);
  }
);