import "@/index.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { useState, useEffect, createContext, useContext } from "react";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";

// Auth Context
const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

const SESSION_KEY = "pb_session_v2";

function App() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(SESSION_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed?.token && parsed?.center) {
          setSession(parsed);
        }
      }
    } catch (e) {
      console.error("Session load error:", e);
    }
    setLoading(false);
  }, []);

  const login = (data) => {
    setSession(data);
    localStorage.setItem(SESSION_KEY, JSON.stringify(data));
  };

  const logout = () => {
    setSession(null);
    localStorage.removeItem(SESSION_KEY);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ session, login, logout }}>
      <BrowserRouter>
        <Routes>
          <Route 
            path="/login" 
            element={session ? <Navigate to="/" replace /> : <Login />} 
          />
          <Route 
            path="/*" 
            element={session ? <Dashboard /> : <Navigate to="/login" replace />} 
          />
        </Routes>
      </BrowserRouter>
      <Toaster 
        position="top-right" 
        richColors 
        closeButton
        toastOptions={{
          style: { fontFamily: 'Manrope, sans-serif' }
        }}
      />
    </AuthContext.Provider>
  );
}

export default App;
