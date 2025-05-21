#!/usr/bin/env python
"""
Script to test Firebase connection using Application Default Credentials.
This is an alternative approach when service account JSON files have issues.
"""

import firebase_admin
from firebase_admin import credentials, firestore

def test_with_application_default():
    """Test Firebase connection using Application Default Credentials."""
    print("🔥 Firebase Application Default Credentials Test 🔥")
    print("------------------------------------------------")
    
    try:
        # Initialize Firebase with Application Default Credentials
        print("🔄 Initializing Firebase with Application Default Credentials...")
        
        # Use Application Default Credentials
        cred = credentials.ApplicationDefault()
        
        # Initialize Firebase with project ID
        firebase_app = firebase_admin.initialize_app(cred, {
            'projectId': 'compliance-d0f59',
        })
        
        print(f"✅ Firebase initialized successfully with app name: {firebase_app.name}")
        
        # Test Firestore connection
        print("\n🔄 Testing Firestore connection...")
        db = firestore.client()
        
        # Try a simple operation
        collections = db.collections()
        collection_names = [collection.id for collection in collections]
        
        print(f"✅ Successfully connected to Firestore")
        print(f"📚 Available collections: {collection_names}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("⚠️ Before running this script, make sure you have:")
    print("  1. Installed the Google Cloud SDK")
    print("  2. Run 'gcloud auth application-default login'")
    print("  3. Selected the correct project with 'gcloud config set project compliance-d0f59'")
    print("")
    
    success = test_with_application_default()
    
    if success:
        print("\n✅ Firebase connection with Application Default Credentials successful!")
        
        # Provide instructions for updating the code
        print("\nTo update your Firebase initialization code, replace the current code in")
        print("backend/app/core/firebase_init.py with:")
        print("\n```python")
        print("import firebase_admin")
        print("from firebase_admin import credentials")
        print("")
        print("def initialize_firebase():")
        print("    try:")
        print("        # Check if Firebase Admin SDK is already initialized")
        print("        if not firebase_admin._apps:")
        print("            # Use Application Default Credentials")
        print("            cred = credentials.ApplicationDefault()")
        print("            firebase_app = firebase_admin.initialize_app(cred, {")
        print("                'projectId': 'compliance-d0f59',")
        print("            })")
        print("            print(f\"✅ Firebase Admin SDK initialized successfully with default app\")")
        print("            return firebase_app")
        print("        else:")
        print("            # Use existing app")
        print("            firebase_app = firebase_admin.get_app()")
        print("            print(f\"✅ Firebase Admin SDK already initialized, using existing app\")")
        print("            return firebase_app")
        print("    except Exception as e:")
        print("        print(f\"❌ Error initializing Firebase Admin SDK: {str(e)}\")")
        print("        raise")
        print("")
        print("# Initialize Firebase when this module is imported")
        print("firebase_app = initialize_firebase()")
        print("```")
        
        exit(0)
    else:
        print("\n❌ Firebase connection with Application Default Credentials failed!")
        print("\nPlease make sure you have:")
        print("  1. Installed the Google Cloud SDK")
        print("  2. Run 'gcloud auth application-default login'")
        print("  3. Selected the correct project with 'gcloud config set project compliance-d0f59'")
        
        exit(1)
