import React, { useState, useEffect } from "react";
import {
  getAuth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
} from "firebase/auth";
import { app } from "../lib/firebase";
import { verifyFirebaseToken } from "../services/complianceService";

/**
 * This is a test component for Firebase authentication.
 * It allows testing email/password signup, signin, and token verification.
 */
const FirebaseAuthTest: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [user, setUser] = useState<any>(null);
  const [token, setToken] = useState<string | null>(null);
  const [verificationResult, setVerificationResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const auth = getAuth(app);

  // Listen for auth state changes
  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((user) => {
      setUser(user);
      setToken(null); // Reset token when user changes
      setVerificationResult(null); // Reset verification result
    });

    return () => unsubscribe();
  }, [auth]);

  // Handle signup
  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const userCredential = await createUserWithEmailAndPassword(
        auth,
        email,
        password
      );
      console.log("User created:", userCredential.user);
    } catch (error: any) {
      setError(`Signup error: ${error.message}`);
      console.error("Signup error:", error);
    } finally {
      setLoading(false);
    }
  };

  // Handle signin
  const handleSignin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const userCredential = await signInWithEmailAndPassword(
        auth,
        email,
        password
      );
      console.log("User signed in:", userCredential.user);
    } catch (error: any) {
      setError(`Signin error: ${error.message}`);
      console.error("Signin error:", error);
    } finally {
      setLoading(false);
    }
  };

  // Handle signout
  const handleSignout = async () => {
    setError(null);
    setLoading(true);

    try {
      await signOut(auth);
      console.log("User signed out");
    } catch (error: any) {
      setError(`Signout error: ${error.message}`);
      console.error("Signout error:", error);
    } finally {
      setLoading(false);
    }
  };

  // Get ID token
  const getIdToken = async () => {
    setError(null);
    setLoading(true);

    try {
      if (!user) {
        throw new Error("No user is signed in");
      }

      const token = await user.getIdToken();
      setToken(token);
      console.log("Token:", token);
    } catch (error: any) {
      setError(`Get token error: ${error.message}`);
      console.error("Get token error:", error);
    } finally {
      setLoading(false);
    }
  };

  // Verify token with backend
  const verifyToken = async () => {
    setError(null);
    setLoading(true);

    try {
      if (!token) {
        throw new Error("No token available");
      }

      const result = await verifyFirebaseToken(token);
      setVerificationResult(result);
      console.log("Verification result:", result);
    } catch (error: any) {
      setError(`Verification error: ${error.message}`);
      console.error("Verification error:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-md mx-auto bg-zinc-900 rounded-lg shadow-lg">
      <h1 className="text-2xl font-bold mb-6 text-white">Firebase Auth Test</h1>

      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded-md text-red-200 text-sm">
          {error}
        </div>
      )}

      {user ? (
        <div className="mb-6">
          <div className="p-4 bg-zinc-800 rounded-md mb-4">
            <h2 className="text-lg font-semibold mb-2 text-white">
              Signed In User
            </h2>
            <p className="text-zinc-300">Email: {user.email}</p>
            <p className="text-zinc-300">UID: {user.uid}</p>
          </div>

          <div className="flex gap-2 mb-4">
            <button
              onClick={getIdToken}
              disabled={loading}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
            >
              Get ID Token
            </button>

            <button
              onClick={handleSignout}
              disabled={loading}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
            >
              Sign Out
            </button>
          </div>

          {token && (
            <div className="mb-4">
              <div className="p-4 bg-zinc-800 rounded-md mb-2">
                <h2 className="text-lg font-semibold mb-2 text-white">
                  ID Token
                </h2>
                <p className="text-zinc-300 break-all text-xs">{token}</p>
              </div>

              <button
                onClick={verifyToken}
                disabled={loading}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                Verify Token with Backend
              </button>
            </div>
          )}

          {verificationResult && (
            <div className="p-4 bg-zinc-800 rounded-md">
              <h2 className="text-lg font-semibold mb-2 text-white">
                Verification Result
              </h2>
              <pre className="text-zinc-300 text-xs overflow-auto">
                {JSON.stringify(verificationResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      ) : (
        <form className="space-y-4">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-zinc-300 mb-1"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-md text-white"
              required
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-zinc-300 mb-1"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-md text-white"
              required
            />
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleSignup}
              disabled={loading}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
            >
              Sign Up
            </button>

            <button
              type="button"
              onClick={handleSignin}
              disabled={loading}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
            >
              Sign In
            </button>
          </div>
        </form>
      )}

      {loading && (
        <div className="mt-4 flex justify-center">
          <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-indigo-500"></div>
        </div>
      )}
    </div>
  );
};

export default FirebaseAuthTest;
