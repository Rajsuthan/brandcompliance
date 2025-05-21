#!/usr/bin/env python
"""
Test script for the new Firebase initialization module.
This script tests the new Firebase initialization module with multiple authentication methods.
"""

import sys
import os
import importlib.util
from firebase_admin import firestore

def test_new_firebase_init():
    """Test the new Firebase initialization module."""
    print("🔥 Testing New Firebase Initialization 🔥")
    print("---------------------------------------")
    
    # Import the new Firebase initialization module
    module_path = os.path.join("app", "core", "firebase_init_new.py")
    if not os.path.exists(module_path):
        print(f"❌ Error: Module not found at {module_path}")
        return False
    
    try:
        # Load the module dynamically
        print(f"📄 Loading module from: {module_path}")
        spec = importlib.util.spec_from_file_location("firebase_init_new", module_path)
        firebase_init_new = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(firebase_init_new)
        
        # Get the Firebase app
        firebase_app = firebase_init_new.firebase_app
        
        if firebase_app is None:
            print("❌ Firebase initialization failed")
            return False
        
        print(f"✅ Firebase initialized successfully with app name: {firebase_app.name}")
        
        # Test Firestore connection
        print("\n🔄 Testing Firestore connection...")
        try:
            db = firestore.client(app=firebase_app)
            # Try a simple operation
            collections = db.collections()
            collection_names = [collection.id for collection in collections]
            print(f"✅ Successfully connected to Firestore")
            print(f"📚 Available collections: {collection_names}")
            return True
        except Exception as e:
            print(f"❌ Error connecting to Firestore: {str(e)}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_new_firebase_init()
    
    if success:
        print("\n✅ New Firebase initialization test passed!")
        print("\nTo use this new implementation:")
        print("1. Rename the current firebase_init.py to firebase_init_old.py")
        print("2. Rename firebase_init_new.py to firebase_init.py")
        print("3. Restart your application")
        exit(0)
    else:
        print("\n❌ New Firebase initialization test failed!")
        exit(1)
