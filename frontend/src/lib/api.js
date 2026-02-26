import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_URL = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000, // 30 second timeout
});

// Request interceptor - add token from localStorage if available
api.interceptors.request.use(
  (config) => {
    const session = localStorage.getItem("session");
    if (session) {
      try {
        const parsed = JSON.parse(session);
        if (parsed.token) {
          // Add token to query params if not already present
          if (config.method === 'get' && !config.params?.token) {
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

// Response interceptor - handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.error("API 401 Error - Token invalid or expired");
      // Don't automatically logout - just log the error
      // The component will show appropriate message
    }
    return Promise.reject(error);
  }
);

// Centers list
export const CENTERS = [
  { code: "PB-HSR", name: "Purnabramha HSR - Bangalore" },
  { code: "PB-TH", name: "Purnabramha Thane - Mumbai" },
  { code: "PB-SN", name: "Purnabramha Sambhajinagar" },
  { code: "PB-DV", name: "Purnabramha Dombivli - Mumbai" },
  { code: "PB-HW", name: "Purnabramha Hinjawadi - Pune" },
  { code: "PB-KN", name: "Purnabramha Kharadi Nyati - Pune" },
  { code: "PB-KAL", name: "Purnabramha Kalyan" },
  { code: "PB-PERTH", name: "Purnabramha Perth - Australia" },
  { code: "PB-MGT", name: "Purnabramha Management (HQ)" },
];

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
