import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

// Suppress ResizeObserver loop error (non-critical, common with Radix UI components)
const resizeObserverErr = window.onerror;
window.onerror = function (message, source, lineno, colno, error) {
  if (message && message.includes && message.includes('ResizeObserver loop')) {
    return true;
  }
  if (resizeObserverErr) {
    return resizeObserverErr(message, source, lineno, colno, error);
  }
  return false;
};

// Also handle unhandled promise rejections for ResizeObserver
window.addEventListener('error', (event) => {
  if (event.message && event.message.includes('ResizeObserver loop')) {
    event.stopImmediatePropagation();
    event.preventDefault();
  }
});

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
