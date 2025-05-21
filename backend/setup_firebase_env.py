#!/usr/bin/env python
"""
Script to set up Firebase credentials as an environment variable.
This script reads the service account JSON file and formats it for use as an environment variable.
"""

import json
import os
import sys

def setup_firebase_env(file_path, output_file=".env.firebase"):
    """
    Set up Firebase credentials as an environment variable.
    
    Args:
        file_path: Path to the service account JSON file
        output_file: Path to the output .env file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Reading service account file: {file_path}")
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Format the private key for environment variable
        if 'private_key' in data:
            # Replace newlines with escaped newlines
            data['private_key'] = data['private_key'].replace('\n', '\\n')
        
        # Convert to JSON string
        env_value = json.dumps(data)
        
        # Write to .env file
        with open(output_file, 'w') as f:
            f.write(f"FIREBASE_CREDENTIALS='{env_value}'\n")
        
        print(f"✅ Firebase credentials written to {output_file}")
        print(f"To use these credentials, run:")
        print(f"  source {output_file}")
        print(f"Or add the contents to your existing .env file")
        
        return True
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Main function."""
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Default path
        file_path = "./app/auth/firebase-service-account.json"
    
    output_file = ".env.firebase"
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    print("🔥 Firebase Environment Variable Setup 🔥")
    print("---------------------------------------")
    
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        return 1
    
    success = setup_firebase_env(file_path, output_file)
    
    if success:
        print("\n✅ Firebase environment variable setup completed!")
        return 0
    else:
        print("\n❌ Failed to set up Firebase environment variable")
        return 1

if __name__ == "__main__":
    sys.exit(main())
