import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import App from "@/App";
import MainLayout from "@/components/layout/MainLayout";
import ComplianceHistory from "@/components/compliance/ComplianceHistory";
import ComplianceDetail from "@/components/compliance/ComplianceDetail";
import ActivityPage from "@/components/account/ActivityPage";
import { useAuth } from "@/lib/auth-context";

const AppRoutes: React.FC = () => {
  const { user, loading, isEmailVerified } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-zinc-950 text-white">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  if (!user || !isEmailVerified) {
    // This will be handled by ProtectedApp
    return null;
  }

  return (
    <Routes>
      <Route
        path="/"
        element={
          <MainLayout>
            <App />
          </MainLayout>
        }
      />
      <Route
        path="/compliance/history"
        element={
          <MainLayout>
            <ComplianceHistory />
          </MainLayout>
        }
      />
      <Route
        path="/compliance/analysis/:analysisId"
        element={
          <MainLayout>
            <ComplianceDetail />
          </MainLayout>
        }
      />
      <Route
        path="/account/activity"
        element={
          <MainLayout>
            <ActivityPage />
          </MainLayout>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default AppRoutes;
