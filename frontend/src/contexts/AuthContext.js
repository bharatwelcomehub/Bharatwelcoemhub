import { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      setToken(storedToken);
      try {
        const response = await axios.get(`${API}/auth/me`, {
          headers: { Authorization: `Bearer ${storedToken}` },
          withCredentials: true
        });
        setUser(response.data);
      } catch (error) {
        console.error('Auth check failed:', error);
        // Try with cookie auth
        try {
          const response = await axios.get(`${API}/auth/me`, {
            withCredentials: true
          });
          setUser(response.data);
        } catch (err) {
          logout();
        }
      }
    }
    setLoading(false);
  };

  const login = async (email, password) => {
    const response = await axios.post(`${API}/auth/login`, { email, password });
    const { token: newToken, user: userData } = response.data;
    setToken(newToken);
    setUser(userData);
    localStorage.setItem('token', newToken);
    return userData;
  };

  const register = async (userData) => {
    const response = await axios.post(`${API}/auth/register`, userData);
    const { token: newToken, user: newUser } = response.data;
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem('token', newToken);
    return newUser;
  };

  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  const loginWithGoogle = () => {
    const redirectUrl = window.location.origin + '/auth/callback';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const handleGoogleCallback = async (sessionId) => {
    try {
      const response = await axios.post(
        `${API}/auth/google/session`,
        { session_id: sessionId },
        { withCredentials: true }
      );
      const { token: newToken, user: userData } = response.data;
      setToken(newToken);
      setUser(userData);
      localStorage.setItem('token', newToken);
      return userData;
    } catch (error) {
      console.error('Google auth failed:', error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
    } catch (error) {
      console.error('Logout error:', error);
    }
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
  };

  const setUserData = (userData) => {
    setUser(userData);
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      token, 
      login, 
      register, 
      logout, 
      loading,
      loginWithGoogle,
      handleGoogleCallback,
      setUserData,
      checkAuth
    }}>
      {children}
    </AuthContext.Provider>
  );
};
