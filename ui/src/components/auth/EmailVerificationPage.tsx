import React, { useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';

const EmailVerificationPage: React.FC = () => {
  const { user, signOut, sendVerificationEmail } = useAuth();
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  
  const handleResendVerification = async () => {
    if (!user) return;
    
    setSending(true);
    try {
      await sendVerificationEmail();
      setSent(true);
      setTimeout(() => setSent(false), 5000); // Reset after 5 seconds
    } catch (error) {
      console.error('Error sending verification email:', error);
    } finally {
      setSending(false);
    }
  };
  
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-zinc-950 text-white p-4">
      <div className="w-full max-w-md p-8 space-y-8 bg-zinc-900 rounded-lg shadow-lg border border-zinc-800">
        <div className="text-center">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-white to-indigo-300 bg-clip-text text-transparent">
            Email Verification Required
          </h1>
          <div className="mt-2 text-zinc-400">
            <p>We've sent a verification email to:</p>
            <p className="font-medium text-white mt-1">{user?.email}</p>
          </div>
        </div>
        
        <div className="bg-zinc-800 p-4 rounded-lg border border-zinc-700">
          <h2 className="font-medium mb-2">Next steps:</h2>
          <ol className="list-decimal list-inside space-y-2 text-zinc-300">
            <li>Check your email inbox</li>
            <li>Click the verification link in the email</li>
            <li>Return to this page and refresh</li>
          </ol>
        </div>
        
        <div className="flex flex-col space-y-4">
          <Button
            onClick={handleResendVerification}
            disabled={sending}
            className="w-full"
          >
            {sending ? 'Sending...' : 'Resend Verification Email'}
          </Button>
          
          {sent && (
            <div className="p-3 bg-green-900/30 border border-green-800 rounded-md text-green-200 text-sm text-center">
              Verification email sent!
            </div>
          )}
          
          <Button
            onClick={() => window.location.reload()}
            variant="outline"
            className="w-full"
          >
            I've Verified My Email
          </Button>
          
          <Button
            onClick={() => signOut()}
            variant="ghost"
            className="text-zinc-400 hover:text-zinc-300"
          >
            Sign Out
          </Button>
        </div>
        
        <div className="mt-6 text-sm text-zinc-500 text-center">
          <p>
            If you don't receive the email, check your spam folder or try resending the verification email.
          </p>
        </div>
      </div>
    </div>
  );
};

export default EmailVerificationPage;
