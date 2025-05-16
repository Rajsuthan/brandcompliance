import React, { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";

enum AuthMode {
  LOGIN,
  SIGNUP,
  RESET_PASSWORD,
}

const LoginPage: React.FC = () => {
  const {
    signInWithGoogle,
    signInWithEmail,
    signUpWithEmail,
    resetPassword,
    error,
  } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<AuthMode>(AuthMode.LOGIN);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSuccessMessage(null);

    try {
      if (mode === AuthMode.LOGIN) {
        await signInWithEmail(email, password);
      } else if (mode === AuthMode.SIGNUP) {
        await signUpWithEmail(email, password);
      } else if (mode === AuthMode.RESET_PASSWORD) {
        await resetPassword(email);
        setSuccessMessage("Password reset email sent. Check your inbox.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-zinc-950 text-white p-4">
      <div className="w-full max-w-md p-8 space-y-8 bg-zinc-900 rounded-lg shadow-lg border border-zinc-800">
        <div className="text-center">
          <h1 className="!text-2xl font-bold bg-gradient-to-r from-white to-indigo-300 bg-clip-text text-transparent">
            Brand Compliance Checker
          </h1>
          <p className="mt-2 text-zinc-400">
            {mode === AuthMode.LOGIN &&
              "Sign in to access your brand compliance dashboard"}
            {mode === AuthMode.SIGNUP && "Create an account to get started"}
            {mode === AuthMode.RESET_PASSWORD && "Reset your password"}
          </p>
        </div>

        {error && (
          <div className="p-3 bg-red-900/30 border border-red-800 rounded-md text-red-200 text-sm">
            {error}
          </div>
        )}

        {successMessage && (
          <div className="p-3 bg-green-900/30 border border-green-800 rounded-md text-green-200 text-sm">
            {successMessage}
          </div>
        )}

        <form onSubmit={handleEmailAuth} className="mt-8 space-y-6">
          <div className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-zinc-300"
              >
                Email Address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {mode !== AuthMode.RESET_PASSWORD && (
              <div>
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-zinc-300"
                >
                  Password
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete={
                    mode === AuthMode.LOGIN
                      ? "current-password"
                      : "new-password"
                  }
                  required={mode === AuthMode.LOGIN || mode === AuthMode.SIGNUP}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            )}
          </div>

          <div>
            <Button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              {isSubmitting
                ? "Processing..."
                : mode === AuthMode.LOGIN
                ? "Sign In"
                : mode === AuthMode.SIGNUP
                ? "Sign Up"
                : "Reset Password"}
            </Button>
          </div>
        </form>

        <div className="mt-6">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-zinc-700"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-zinc-900 text-zinc-400">
                Or continue with
              </span>
            </div>
          </div>

          <div className="mt-6">
            <Button
              onClick={signInWithGoogle}
              disabled={isSubmitting}
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
            </Button>
          </div>
        </div>

        <div className="mt-6 text-center text-sm">
          {mode === AuthMode.LOGIN && (
            <>
              <button
                type="button"
                onClick={() => setMode(AuthMode.RESET_PASSWORD)}
                className="text-indigo-400 hover:text-indigo-300 focus:outline-none"
              >
                Forgot your password?
              </button>
              <div className="mt-2">
                Don't have an account?{" "}
                <button
                  type="button"
                  onClick={() => setMode(AuthMode.SIGNUP)}
                  className="text-indigo-400 hover:text-indigo-300 focus:outline-none"
                >
                  Sign up
                </button>
              </div>
            </>
          )}
          {mode === AuthMode.SIGNUP && (
            <div>
              Already have an account?{" "}
              <button
                type="button"
                onClick={() => setMode(AuthMode.LOGIN)}
                className="text-indigo-400 hover:text-indigo-300 focus:outline-none"
              >
                Sign in
              </button>
            </div>
          )}
          {mode === AuthMode.RESET_PASSWORD && (
            <div>
              <button
                type="button"
                onClick={() => setMode(AuthMode.LOGIN)}
                className="text-indigo-400 hover:text-indigo-300 focus:outline-none"
              >
                Back to sign in
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
