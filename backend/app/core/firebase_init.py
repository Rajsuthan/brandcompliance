"""
Firebase initialization module.
This module provides a centralized place to initialize Firebase Admin SDK.
"""

import os
import json
import firebase_admin
from firebase_admin import credentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Firebase Admin SDK
def initialize_firebase():
    """
    Initialize Firebase Admin SDK if not already initialized.

    Returns:
        firebase_admin.App: Firebase app instance
    """
    try:
        # Check if Firebase Admin SDK is already initialized
        if not firebase_admin._apps:
            # First try to load from environment variable (preferred method)
            cred_json = os.getenv("FIREBASE_CREDENTIALS")
            if cred_json:
                try:
                    cred_dict = json.loads(cred_json)
                    cred = credentials.Certificate(cred_dict)
                    print(f"✅ Using Firebase credentials from environment variable")
                except json.JSONDecodeError as e:
                    print(f"❌ Error parsing FIREBASE_CREDENTIALS environment variable: {str(e)}")
                    raise ValueError("FIREBASE_CREDENTIALS environment variable contains invalid JSON")
            else:
                # Fallback to file-based credentials
                cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "app/auth/firebase-service-account.json")
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    print(f"✅ Using Firebase credentials from file: {cred_path}")
                else:
                    raise ValueError("Firebase credentials not found. Please set FIREBASE_CREDENTIALS environment variable or provide a valid credentials file")

            # Initialize the Firebase app with default name
            firebase_app = firebase_admin.initialize_app(cred)
            print(f"✅ Firebase Admin SDK initialized successfully with default app")
            return firebase_app
        else:
            # Use existing app
            firebase_app = firebase_admin.get_app()
            print(f"✅ Firebase Admin SDK already initialized, using existing app")
            return firebase_app
    except Exception as e:
        print(f"❌ Error initializing Firebase Admin SDK: {str(e)}")
        raise

# Initialize Firebase when this module is imported
firebase_app = initialize_firebase()
