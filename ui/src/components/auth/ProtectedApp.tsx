import React from "react";
import { useAuth } from "@/lib/auth-context";
import LoginPage from "./LoginPage";
import EmailVerificationPage from "./EmailVerificationPage";
import AppRoutes from "@/components/AppRoutes";

const ProtectedApp: React.FC = () => {
  const { user, loading, isEmailVerified, isAuthReady } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-zinc-950 text-white">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  // Not logged in - show login page
  if (!user) {
    return <LoginPage />;
  }

  // Logged in but email not verified - show verification page
  if (isAuthReady && !isEmailVerified) {
    return <EmailVerificationPage />;
  }

  // Logged in and verified - show app routes
  return <AppRoutes />;
};

export default ProtectedApp;
