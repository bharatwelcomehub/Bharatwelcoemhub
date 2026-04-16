import { useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';

const AuthCallback = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { handleGoogleCallback } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Prevent double processing in StrictMode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      // Extract session_id from URL fragment
      const hash = location.hash;
      const params = new URLSearchParams(hash.replace('#', ''));
      const sessionId = params.get('session_id');

      if (!sessionId) {
        toast.error('Authentication failed');
        navigate('/');
        return;
      }

      try {
        const user = await handleGoogleCallback(sessionId);
        toast.success(`Welcome, ${user.name || user.email}!`);
        // Navigate back to where user was (or home)
        const returnTo = localStorage.getItem('auth_return_to') || '/';
        localStorage.removeItem('auth_return_to');
        navigate(returnTo, { state: { user }, replace: true });
      } catch (error) {
        console.error('Auth callback error:', error);
        toast.error('Failed to complete login');
        navigate('/');
      }
    };

    processAuth();
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-[hsl(30,20%,97%)] to-white">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
        <p className="text-foreground/70 font-manrope">Completing login...</p>
      </div>
    </div>
  );
};

export default AuthCallback;
