import React, { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { useNavigate } from 'react-router-dom';

/**
 * This component handles the redirect after email verification.
 * It checks if the user's email is verified and redirects to the main app.
 */
const VerificationHandler: React.FC = () => {
  const { user, isEmailVerified, loading } = useAuth();
  const [verificationStatus, setVerificationStatus] = useState<'checking' | 'success' | 'error'>('checking');
  const navigate = useNavigate();

  useEffect(() => {
    // If still loading, wait
    if (loading) return;

    // If no user, redirect to login
    if (!user) {
      navigate('/');
      return;
    }

    // Check if email is verified
    if (isEmailVerified) {
      setVerificationStatus('success');
      // Redirect to main app after a short delay
      const timer = setTimeout(() => {
        navigate('/');
      }, 2000);
      return () => clearTimeout(timer);
    } else {
      // Force reload user to check verification status again
      const checkVerification = async () => {
        try {
          await user.reload();
          if (user.emailVerified) {
            setVerificationStatus('success');
            // Redirect to main app after a short delay
            setTimeout(() => {
              navigate('/');
            }, 2000);
          } else {
            setVerificationStatus('error');
          }
        } catch (error) {
          console.error('Error checking verification status:', error);
          setVerificationStatus('error');
        }
      };
      
      checkVerification();
    }
  }, [user, isEmailVerified, loading, navigate]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-zinc-950 text-white p-4">
      <div className="w-full max-w-md p-8 space-y-8 bg-zinc-900 rounded-lg shadow-lg border border-zinc-800">
        <div className="text-center">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-white to-indigo-300 bg-clip-text text-transparent">
            Email Verification
          </h1>
          
          {verificationStatus === 'checking' && (
            <>
              <div className="mt-6 flex justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
              </div>
              <p className="mt-4 text-zinc-400">Checking verification status...</p>
            </>
          )}
          
          {verificationStatus === 'success' && (
            <>
              <div className="mt-6 flex justify-center">
                <div className="h-12 w-12 rounded-full bg-green-500 flex items-center justify-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              </div>
              <p className="mt-4 text-zinc-400">Your email has been verified successfully!</p>
              <p className="mt-2 text-zinc-400">Redirecting to the app...</p>
            </>
          )}
          
          {verificationStatus === 'error' && (
            <>
              <div className="mt-6 flex justify-center">
                <div className="h-12 w-12 rounded-full bg-red-500 flex items-center justify-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
              </div>
              <p className="mt-4 text-zinc-400">There was an issue verifying your email.</p>
              <p className="mt-2 text-zinc-400">Please try clicking the verification link again.</p>
              <button 
                onClick={() => navigate('/')}
                className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                Return to App
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default VerificationHandler;
