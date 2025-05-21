#!/usr/bin/env python
"""
Test script for Firebase connection.
This script attempts to initialize Firebase using the service account file
and performs a simple Firestore operation to verify the connection.
"""

import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

def test_firebase_connection():
    """Test Firebase connection using the service account file."""
    print("🔥 Firebase Connection Test 🔥")
    print("-----------------------------")
    
    # Path to the service account file
    cred_path = "./app/auth/firebase-service-account.json"
    
    if not os.path.exists(cred_path):
        print(f"❌ Error: Service account file not found at {cred_path}")
        return False
    
    print(f"📄 Found service account file at: {cred_path}")
    
    try:
        # Print file info
        file_size = os.path.getsize(cred_path)
        print(f"📊 File size: {file_size} bytes")
        
        # Load and validate the JSON
        with open(cred_path, 'r') as f:
            cred_data = json.load(f)
        
        required_fields = [
            "type", "project_id", "private_key_id", "private_key", 
            "client_email", "client_id", "auth_uri", "token_uri"
        ]
        
        missing_fields = [field for field in required_fields if field not in cred_data]
        if missing_fields:
            print(f"❌ Error: Missing required fields: {', '.join(missing_fields)}")
            return False
        
        print(f"✅ Service account JSON contains all required fields")
        print(f"📋 Project ID: {cred_data.get('project_id')}")
        print(f"📧 Client email: {cred_data.get('client_email')}")
        
        # Initialize Firebase with direct file path
        print("\n🔄 Initializing Firebase with direct file path...")
        try:
            cred = credentials.Certificate(cred_path)
            firebase_app = firebase_admin.initialize_app(cred)
            print(f"✅ Firebase initialized successfully with app name: {firebase_app.name}")
        except Exception as e:
            print(f"❌ Error initializing Firebase with direct file path: {str(e)}")
            print("\n🔄 Trying with parsed JSON data...")
            
            try:
                # Try with parsed JSON data
                cred = credentials.Certificate(cred_data)
                firebase_app = firebase_admin.initialize_app(cred)
                print(f"✅ Firebase initialized successfully with app name: {firebase_app.name}")
            except Exception as e2:
                print(f"❌ Error initializing Firebase with parsed JSON data: {str(e2)}")
                return False
        
        # Test Firestore connection
        print("\n🔄 Testing Firestore connection...")
        try:
            db = firestore.client()
            # Try a simple operation
            collections = db.collections()
            collection_names = [collection.id for collection in collections]
            print(f"✅ Successfully connected to Firestore")
            print(f"📚 Available collections: {collection_names}")
            return True
        except Exception as e:
            print(f"❌ Error connecting to Firestore: {str(e)}")
            return False
    
    except json.JSONDecodeError as e:
        print(f"❌ Error: Service account file contains invalid JSON: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_firebase_connection()
    
    if success:
        print("\n✅ Firebase connection test passed!")
        exit(0)
    else:
        print("\n❌ Firebase connection test failed!")
        exit(1)
