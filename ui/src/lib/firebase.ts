import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'firebase/auth';
import { getAnalytics } from 'firebase/analytics';

// Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyC-XflEb5X9rZ8NG7NBS8g2fY6RhY8CLcY",
  authDomain: "compliance-d0f59.firebaseapp.com",
  projectId: "compliance-d0f59",
  storageBucket: "compliance-d0f59.firebasestorage.app",
  messagingSenderId: "97495397709",
  appId: "1:97495397709:web:de521670a44933fc66b304",
  measurementId: "G-EDM0QGHLZ6"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const analytics = getAnalytics(app);
const googleProvider = new GoogleAuthProvider();

export { app, auth, analytics, googleProvider };
