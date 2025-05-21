#!/usr/bin/env python
"""
Script to fix Firebase service account JSON file.

This script can be run directly to fix common issues with the Firebase service account JSON file,
such as escaped newlines in the private key.

Usage:
    python fix_firebase_credentials.py [file_path]

If file_path is not provided, the script will look for the service account JSON file in the default locations.
"""

import sys
import os
from app.core.firebase_init import fix_firebase_credentials

def main():
    """Main function to fix Firebase credentials."""
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    print("🔧 Firebase Credentials Fixer 🔧")
    print("--------------------------------")
    
    if file_path:
        print(f"Using specified file path: {file_path}")
    else:
        print("No file path specified, will try default locations")
    
    success = fix_firebase_credentials(file_path)
    
    if success:
        print("\n✅ Firebase credentials fixed successfully!")
        return 0
    else:
        print("\n❌ Failed to fix Firebase credentials")
        return 1

if __name__ == "__main__":
    sys.exit(main())
