import React, { createContext, useContext, useEffect, useState } from "react";
import {
  User,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  sendPasswordResetEmail,
  sendEmailVerification,
} from "firebase/auth";
import { auth, googleProvider } from "./firebase";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  isEmailVerified: boolean;
  isAuthReady: boolean; // Indicates if auth is ready but waiting for verification
  signInWithGoogle: () => Promise<void>;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  signUpWithEmail: (email: string, password: string) => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  sendVerificationEmail: () => Promise<void>;
  signOut: () => Promise<void>;
  getIdToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEmailVerified, setIsEmailVerified] = useState(false);
  const [isAuthReady, setIsAuthReady] = useState(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setUser(user);

      if (user) {
        // Check if user is verified (either email is verified or using Google auth)
        const verified =
          user.emailVerified ||
          user.providerData.some(
            (provider) => provider.providerId === "google.com"
          );

        setIsEmailVerified(verified);

        // User is authenticated but may not be verified
        setIsAuthReady(true);
      } else {
        // No user, reset states
        setIsEmailVerified(false);
        setIsAuthReady(false);
      }

      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const signInWithGoogle = async () => {
    setError(null);
    try {
      await signInWithPopup(auth, googleProvider);
    } catch (error: any) {
      console.error("Error signing in with Google:", error);
      setError(error.message || "Failed to sign in with Google");
    }
  };

  const signInWithEmail = async (email: string, password: string) => {
    setError(null);
    try {
      await signInWithEmailAndPassword(auth, email, password);
    } catch (error: any) {
      console.error("Error signing in with email:", error);
      setError(error.message || "Failed to sign in with email and password");
    }
  };

  const signUpWithEmail = async (email: string, password: string) => {
    setError(null);
    try {
      const userCredential = await createUserWithEmailAndPassword(
        auth,
        email,
        password
      );

      // Configure the action URL with a redirect
      const actionCodeSettings = {
        url: window.location.origin, // Redirect to the app's root URL
        handleCodeInApp: true,
      };

      // Send verification email
      await sendEmailVerification(userCredential.user, actionCodeSettings);
    } catch (error: any) {
      console.error("Error signing up with email:", error);
      setError(error.message || "Failed to create account");
    }
  };

  const resetPassword = async (email: string) => {
    setError(null);
    try {
      // Configure the action URL with a redirect
      const actionCodeSettings = {
        url: window.location.origin, // Redirect to the app's root URL
        handleCodeInApp: true,
      };

      await sendPasswordResetEmail(auth, email, actionCodeSettings);
    } catch (error: any) {
      console.error("Error resetting password:", error);
      setError(error.message || "Failed to send password reset email");
    }
  };

  const signOut = async () => {
    setError(null);
    try {
      await firebaseSignOut(auth);
    } catch (error: any) {
      console.error("Error signing out:", error);
      setError(error.message || "Failed to sign out");
    }
  };

  const getIdToken = async (): Promise<string | null> => {
    if (!user) return null;
    try {
      return await user.getIdToken();
    } catch (error) {
      console.error("Error getting ID token:", error);
      return null;
    }
  };

  const sendVerificationEmail = async (): Promise<void> => {
    setError(null);
    try {
      if (!user) {
        throw new Error("No user is signed in");
      }

      // Configure the action URL with a redirect
      const actionCodeSettings = {
        url: window.location.origin, // Redirect to the app's root URL
        handleCodeInApp: true,
      };

      await sendEmailVerification(user, actionCodeSettings);
    } catch (error: any) {
      console.error("Error sending verification email:", error);
      setError(error.message || "Failed to send verification email");
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        isEmailVerified,
        isAuthReady,
        signInWithGoogle,
        signInWithEmail,
        signUpWithEmail,
        resetPassword,
        sendVerificationEmail,
        signOut,
        getIdToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
