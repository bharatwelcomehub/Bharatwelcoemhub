import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_URL = `${BACKEND_URL}/api`;

// Create axios instance with retry config
export const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000, // 30 second timeout
});

// Session key constant
const SESSION_KEY = "pb_session_v2";

// Request interceptor - add token from localStorage if available
api.interceptors.request.use(
  (config) => {
    const session = localStorage.getItem(SESSION_KEY);
    if (session) {
      try {
        const parsed = JSON.parse(session);
        if (parsed.token) {
          // Add token to query params for GET and DELETE (which carry no body)
          if ((config.method === 'get' || config.method === 'delete') && !config.params?.token) {
            config.params = { ...config.params, token: parsed.token };
          }
        }
      } catch (e) {
        console.error("Failed to parse session:", e);
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle 401 errors with retry logic
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401) {
      console.error("API 401 Error - Token invalid or expired", originalRequest?.url);
      
      // Check if we've already retried this request
      if (!originalRequest._retry) {
        originalRequest._retry = true;
        
        // Check if session still exists in localStorage
        const session = localStorage.getItem(SESSION_KEY);
        if (session) {
          try {
            const parsed = JSON.parse(session);
            if (parsed.token) {
              // Wait a short moment and retry once (handles timing issues)
              await new Promise(resolve => setTimeout(resolve, 500));
              return api(originalRequest);
            }
          } catch (e) {
            console.error("Session parse error during retry:", e);
          }
        }
      }
      
      // DON'T auto-logout - just log the error and let the component handle it
      // This prevents unexpected logouts
      console.warn("401 error after retry - NOT auto-logging out");
    }
    
    // Handle network errors with retry
    if (error.code === 'ECONNABORTED' || error.message === 'Network Error') {
      if (!originalRequest._networkRetry) {
        originalRequest._networkRetry = true;
        console.warn("Network error - retrying request...");
        await new Promise(resolve => setTimeout(resolve, 1000));
        return api(originalRequest);
      }
    }
    
    return Promise.reject(error);
  }
);

// Utility function to make API calls with automatic retry
export const apiWithRetry = async (requestFn, maxRetries = 2) => {
  let lastError;
  for (let i = 0; i <= maxRetries; i++) {
    try {
      return await requestFn();
    } catch (error) {
      lastError = error;
      if (error.response?.status === 401) {
        // Don't retry 401s - they're handled by interceptor
        throw error;
      }
      if (i < maxRetries) {
        console.warn(`Request failed, retrying (${i + 1}/${maxRetries})...`);
        await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
      }
    }
  }
  throw lastError;
};

// Centers list - DEPRECATED: Use fetchCentersFromDB() instead. Kept only as emergency fallback.
export const CENTERS = [];

// Fetch centers from database - PRIMARY method for getting center list
export const fetchCentersFromDB = async (token) => {
  try {
    const res = await api.get(`/centers?token=${token}`);
    if (res.data?.centers && res.data.centers.length > 0) {
      return res.data.centers.map(c => ({
        code: c.code,
        name: c.name,
        country: c.country || "India",
        is_india_center: c.is_india_center !== false,
        phone: c.phone || "",
        email: c.email || "",
        active: c.active !== false
      }));
    }
    return [];
  } catch (err) {
    console.error("Failed to fetch centers from DB:", err);
    return [];
  }
};

// Permission helper: check if user has admin access (replaces all PB-MGT checks)
export const isAdminUser = (session) => {
  return session?.is_super_admin === true || session?.is_admin === true;
};

// Check if a center is international (non-India) — replaces hardcoded PB-PERTH checks
export const isInternationalCenter = (centerCode, centersList) => {
  if (!centerCode || !centersList) return false;
  const center = centersList.find(c => c.code === centerCode);
  if (center) return center.is_india_center === false;
  return false;
};

// Status options
export const STATUS_OPTIONS = [
  { value: "P", label: "Present", color: "status-P" },
  { value: "A", label: "Absent", color: "status-A" },
  { value: "HD", label: "Half Day", color: "status-HD" },
  { value: "WO", label: "Weekly Off", color: "status-WO" },
  { value: "L", label: "Leave", color: "status-L" },
];

// Advance modes
export const ADVANCE_MODES = ["CASH", "GPAY", "NEFT", "ONLINE"];

// Date helpers
export const formatDate = (date) => {
  if (!date) return "";
  const d = new Date(date);
  return d.toISOString().split("T")[0];
};

export const formatMonth = (date) => {
  if (!date) return "";
  const d = new Date(date);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
};

export const getTodayISO = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

export const getCurrentMonth = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
};
