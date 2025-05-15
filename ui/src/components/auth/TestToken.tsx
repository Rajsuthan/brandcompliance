import React, { useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';

const TestToken: React.FC = () => {
  const { getIdToken } = useAuth();
  const [token, setToken] = useState<string | null>(null);
  const [verificationResult, setVerificationResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGetToken = async () => {
    try {
      setLoading(true);
      const newToken = await getIdToken();
      setToken(newToken);
      setError(null);
    } catch (err: any) {
      setError(`Error getting token: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyToken = async () => {
    if (!token) {
      setError('No token to verify');
      return;
    }

    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/firebase-auth/verify-token', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Verification failed: ${response.status} ${response.statusText} - ${errorText}`);
      }

      const result = await response.json();
      setVerificationResult(result);
      setError(null);
    } catch (err: any) {
      setError(`Error verifying token: ${err.message}`);
      setVerificationResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-md mx-auto bg-zinc-900 rounded-lg shadow-lg">
      <h1 className="text-2xl font-bold mb-6 text-white">Test Firebase Token</h1>

      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded-md text-red-200 text-sm">
          {error}
        </div>
      )}

      <div className="space-y-4">
        <Button 
          onClick={handleGetToken} 
          disabled={loading}
          className="w-full"
        >
          Get Firebase Token
        </Button>

        {token && (
          <>
            <div className="p-3 bg-zinc-800 rounded-md">
              <h3 className="text-sm font-medium mb-1 text-zinc-400">Token:</h3>
              <p className="text-xs text-zinc-300 break-all">
                {token}
              </p>
            </div>

            <Button 
              onClick={handleVerifyToken} 
              disabled={loading}
              className="w-full"
            >
              Verify Token with Backend
            </Button>
          </>
        )}

        {verificationResult && (
          <div className="p-3 bg-green-900/30 border border-green-800 rounded-md">
            <h3 className="text-sm font-medium mb-1 text-green-200">Verification Successful:</h3>
            <pre className="text-xs text-green-300 overflow-auto">
              {JSON.stringify(verificationResult, null, 2)}
            </pre>
          </div>
        )}

        {loading && (
          <div className="flex justify-center">
            <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-indigo-500"></div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TestToken;
