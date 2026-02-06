import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';

export default function AuthCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [error, setError] = useState('');

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        if (!code) {
          setError('No authorization code received');
          return;
        }
        // For now, just redirect to login since Google OAuth not fully set up
        setTimeout(() => navigate('/login'), 1000);
      } catch (err) {
        setError(err.response?.data?.message || 'Authentication failed');
        setTimeout(() => navigate('/login'), 2000);
      }
    };
    handleCallback();
  }, [searchParams, navigate]);

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md text-center space-y-4">
          <h2 className="text-xl font-semibold text-red-600">Authentication Failed</h2>
          <p className="text-muted-foreground">{error}</p>
          <p className="text-sm text-muted-foreground">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-md text-center space-y-4">
        <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary" />
        <h2 className="text-xl font-semibold">Completing Sign In</h2>
        <p className="text-muted-foreground">Please wait while we authenticate your account...</p>
      </div>
    </div>
  );
}
