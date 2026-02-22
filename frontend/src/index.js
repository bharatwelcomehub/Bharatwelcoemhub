import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

// Suppress ResizeObserver loop error (non-critical, common with Radix UI components)
// This error is harmless and occurs due to how browsers handle resize observations
if (typeof window !== 'undefined') {
  // Debounce ResizeObserver to prevent loop errors
  const debounce = (fn, delay) => {
    let timeoutId;
    return (...args) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => fn.apply(this, args), delay);
    };
  };

  // Override ResizeObserver to add debouncing
  const OriginalResizeObserver = window.ResizeObserver;
  window.ResizeObserver = class ResizeObserver extends OriginalResizeObserver {
    constructor(callback) {
      super(debounce(callback, 20));
    }
  };

  // Suppress error in console
  const originalError = console.error;
  console.error = (...args) => {
    if (args[0] && typeof args[0] === 'string' && args[0].includes('ResizeObserver')) {
      return;
    }
    originalError.apply(console, args);
  };

  // Suppress in window.onerror
  const resizeObserverErr = window.onerror;
  window.onerror = function (message, source, lineno, colno, error) {
    if (message && typeof message === 'string' && message.includes('ResizeObserver')) {
      return true;
    }
    if (resizeObserverErr) {
      return resizeObserverErr(message, source, lineno, colno, error);
    }
    return false;
  };

  // Suppress in error event listener
  window.addEventListener('error', (event) => {
    if (event.message && event.message.includes('ResizeObserver')) {
      event.stopImmediatePropagation();
      event.preventDefault();
      return true;
    }
  }, true);

  // Suppress unhandled rejections related to ResizeObserver
  window.addEventListener('unhandledrejection', (event) => {
    if (event.reason && event.reason.message && event.reason.message.includes('ResizeObserver')) {
      event.preventDefault();
      return true;
    }
  });
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
