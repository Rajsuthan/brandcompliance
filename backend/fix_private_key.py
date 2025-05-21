#!/usr/bin/env python
"""
Script to fix the private key in a Firebase service account JSON file.
This script ensures the private key is properly formatted with correct newlines.
"""

import json
import os
import sys

def fix_private_key(file_path):
    """
    Fix the private key in a Firebase service account JSON file.
    
    Args:
        file_path: Path to the service account JSON file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Reading service account file: {file_path}")
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if 'private_key' not in data:
            print("Error: No private_key field found in the service account file")
            return False
        
        # Get the original private key
        private_key = data['private_key']
        original_key = private_key
        
        # Check if the private key has the correct format
        if not private_key.startswith("-----BEGIN PRIVATE KEY-----"):
            print("Error: Private key does not start with the correct marker")
            return False
        
        if not private_key.endswith("-----END PRIVATE KEY-----\n") and not private_key.endswith("-----END PRIVATE KEY-----"):
            print("Warning: Private key does not end with the correct marker and newline")
        
        # Fix common issues with the private key
        
        # 1. Replace escaped newlines with actual newlines
        if "\\n" in private_key:
            print("Fixing: Replacing escaped newlines with actual newlines")
            private_key = private_key.replace("\\n", "\n")
        
        # 2. Ensure there's a newline after BEGIN marker
        if "-----BEGIN PRIVATE KEY-----\n" not in private_key and "-----BEGIN PRIVATE KEY-----" in private_key:
            print("Fixing: Adding newline after BEGIN marker")
            private_key = private_key.replace("-----BEGIN PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----\n")
        
        # 3. Ensure there's a newline before END marker
        if "\n-----END PRIVATE KEY-----" not in private_key and "-----END PRIVATE KEY-----" in private_key:
            print("Fixing: Adding newline before END marker")
            private_key = private_key.replace("-----END PRIVATE KEY-----", "\n-----END PRIVATE KEY-----")
        
        # 4. Ensure there's a final newline
        if not private_key.endswith("\n"):
            print("Fixing: Adding final newline")
            private_key += "\n"
        
        # Check if any changes were made
        if private_key == original_key:
            print("No changes needed to the private key")
            return True
        
        # Update the private key in the data
        data['private_key'] = private_key
        
        # Create a backup of the original file
        backup_path = f"{file_path}.bak"
        import shutil
        shutil.copy2(file_path, backup_path)
        print(f"Created backup of original file at: {backup_path}")
        
        # Write the updated data back to the file
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Successfully updated the private key in: {file_path}")
        return True
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def main():
    """Main function."""
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Default path
        file_path = "./app/auth/firebase-service-account.json"
    
    print("🔑 Firebase Private Key Fixer 🔑")
    print("--------------------------------")
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return 1
    
    success = fix_private_key(file_path)
    
    if success:
        print("\n✅ Private key fixed successfully!")
        return 0
    else:
        print("\n❌ Failed to fix private key")
        return 1

if __name__ == "__main__":
    sys.exit(main())
