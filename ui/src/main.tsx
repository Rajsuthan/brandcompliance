import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./index.css";
import { ThemeProvider } from "./components/theme-provider";
import { AuthProvider } from "./lib/auth-context";
import ProtectedApp from "./components/auth/ProtectedApp";
import TestFirebaseAuth from "./test/TestFirebaseAuth";
import VerificationHandler from "./components/auth/VerificationHandler";
import ComplianceHistory from "./components/compliance/ComplianceHistory";
import ComplianceDetail from "./components/compliance/ComplianceDetail";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/test-auth" element={<TestFirebaseAuth />} />
            <Route path="/verified" element={<VerificationHandler />} />
            <Route path="/*" element={<ProtectedApp />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  </StrictMode>
);
