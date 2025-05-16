import React, { useState } from "react";
import { useAuth } from "../lib/auth-context";

/**
 * This is a test component for Firebase authentication with email verification.
 * It allows testing email/password signup, signin, and email verification.
 */
const TestFirebaseAuth: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState<string | null>(null);
  const [localLoading, setLocalLoading] = useState(false);

  // Use the auth context
  const {
    user,
    loading,
    error,
    isEmailVerified,
    signInWithGoogle,
    signInWithEmail,
    signUpWithEmail,
    sendVerificationEmail,
    signOut,
    getIdToken,
  } = useAuth();

  // Handle signin
  const handleSignin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalLoading(true);
    await signInWithEmail(email, password);
    setLocalLoading(false);
  };

  // Handle signup
  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalLoading(true);
    await signUpWithEmail(email, password);
    setLocalLoading(false);
  };

  // Handle signout
  const handleSignout = async () => {
    setLocalLoading(true);
    await signOut();
    setToken(null);
    setLocalLoading(false);
  };

  // Get ID token
  const handleGetIdToken = async () => {
    setLocalLoading(true);
    try {
      const newToken = await getIdToken();
      setToken(newToken);
      console.log("Token:", newToken);
    } catch (error: any) {
      console.error("Get token error:", error);
    } finally {
      setLocalLoading(false);
    }
  };

  // Resend verification email
  const handleResendVerification = async () => {
    setLocalLoading(true);
    await sendVerificationEmail();
    setLocalLoading(false);
  };

  // Test backend verification
  const testBackendVerification = async () => {
    setLocalLoading(true);

    try {
      if (!token) {
        throw new Error("No token available");
      }

      const response = await fetch(
        "http://localhost:8000/api/firebase-auth/verify-token",
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        console.log("Backend verification successful:", data);
        alert("Backend verification successful! Check console for details.");
      } else {
        const errorText = await response.text();
        throw new Error(
          `Backend verification failed: ${response.status} - ${errorText}`
        );
      }
    } catch (error: any) {
      console.error("Backend verification error:", error);
      alert(`Backend verification error: ${error.message}`);
    } finally {
      setLocalLoading(false);
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
            <p className="text-zinc-300">
              Email Verified:{" "}
              <span
                className={isEmailVerified ? "text-green-500" : "text-red-500"}
              >
                {isEmailVerified ? "Yes" : "No"}
              </span>
            </p>
          </div>

          {!isEmailVerified &&
            user.providerData[0]?.providerId === "password" && (
              <div className="mb-4 p-3 bg-yellow-900/30 border border-yellow-800 rounded-md text-yellow-200 text-sm">
                <p className="mb-2">
                  Your email is not verified. Please check your inbox for a
                  verification email.
                </p>
                <button
                  onClick={handleResendVerification}
                  disabled={localLoading || loading}
                  className="text-yellow-400 underline hover:text-yellow-300"
                >
                  Resend verification email
                </button>
              </div>
            )}

          <div className="flex gap-2 mb-4">
            <button
              onClick={handleGetIdToken}
              disabled={localLoading || loading}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
            >
              Get ID Token
            </button>

            <button
              onClick={handleSignout}
              disabled={localLoading || loading}
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
                <p className="text-zinc-300 break-all text-xs">
                  {token.substring(0, 50)}...
                </p>
              </div>

              <button
                onClick={testBackendVerification}
                disabled={localLoading || loading || !isEmailVerified}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                Test Backend Verification
              </button>

              {!isEmailVerified && (
                <p className="mt-2 text-sm text-red-400">
                  You need to verify your email before testing backend
                  verification.
                </p>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          <form onSubmit={handleSignin} className="space-y-4">
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
                type="submit"
                disabled={localLoading || loading}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                Sign In
              </button>

              <button
                type="button"
                onClick={handleSignup}
                disabled={localLoading || loading}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                Sign Up
              </button>
            </div>
          </form>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-zinc-700"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-zinc-900 text-zinc-400">Or</span>
            </div>
          </div>

          <button
            onClick={signInWithGoogle}
            disabled={localLoading || loading}
            className="w-full flex items-center justify-center gap-3 bg-white hover:bg-gray-100 text-gray-800 font-semibold py-2 px-4 rounded shadow"
          >
            <svg
              viewBox="0 0 24 24"
              width="24"
              height="24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <g transform="matrix(1, 0, 0, 1, 27.009001, -39.238998)">
                <path
                  fill="#4285F4"
                  d="M -3.264 51.509 C -3.264 50.719 -3.334 49.969 -3.454 49.239 L -14.754 49.239 L -14.754 53.749 L -8.284 53.749 C -8.574 55.229 -9.424 56.479 -10.684 57.329 L -10.684 60.329 L -6.824 60.329 C -4.564 58.239 -3.264 55.159 -3.264 51.509 Z"
                />
                <path
                  fill="#34A853"
                  d="M -14.754 63.239 C -11.514 63.239 -8.804 62.159 -6.824 60.329 L -10.684 57.329 C -11.764 58.049 -13.134 58.489 -14.754 58.489 C -17.884 58.489 -20.534 56.379 -21.484 53.529 L -25.464 53.529 L -25.464 56.619 C -23.494 60.539 -19.444 63.239 -14.754 63.239 Z"
                />
                <path
                  fill="#FBBC05"
                  d="M -21.484 53.529 C -21.734 52.809 -21.864 52.039 -21.864 51.239 C -21.864 50.439 -21.724 49.669 -21.484 48.949 L -21.484 45.859 L -25.464 45.859 C -26.284 47.479 -26.754 49.299 -26.754 51.239 C -26.754 53.179 -26.284 54.999 -25.464 56.619 L -21.484 53.529 Z"
                />
                <path
                  fill="#EA4335"
                  d="M -14.754 43.989 C -12.984 43.989 -11.404 44.599 -10.154 45.789 L -6.734 42.369 C -8.804 40.429 -11.514 39.239 -14.754 39.239 C -19.444 39.239 -23.494 41.939 -25.464 45.859 L -21.484 48.949 C -20.534 46.099 -17.884 43.989 -14.754 43.989 Z"
                />
              </g>
            </svg>
            Sign in with Google
          </button>
        </div>
      )}

      {(localLoading || loading) && (
        <div className="mt-4 flex justify-center">
          <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-indigo-500"></div>
        </div>
      )}

      <div className="mt-6 text-sm text-zinc-400">
        <p>
          This is a test component for Firebase authentication with email
          verification.
        </p>
        <p>
          When you sign up with email/password, a verification email will be
          sent.
        </p>
        <p>
          You must verify your email before you can use the backend
          verification.
        </p>
      </div>
    </div>
  );
};

export default TestFirebaseAuth;
