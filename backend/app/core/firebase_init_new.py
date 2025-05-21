"""
Firebase initialization module.
This module provides a centralized place to initialize Firebase Admin SDK.
"""

import os
import json
import firebase_admin
from firebase_admin import credentials
from dotenv import load_dotenv
import pathlib

# Load environment variables
load_dotenv()

def fix_service_account_json(file_path, save_fixed=False):
    """
    Fix common issues in a service account JSON file and return the fixed data.
    
    Args:
        file_path: Path to the service account JSON file
        save_fixed: Whether to save the fixed data back to the file
        
    Returns:
        tuple: (fixed_data, message) where fixed_data is the corrected JSON data as a dict
               and message is a string describing what was fixed
    """
    required_fields = [
        "type", "project_id", "private_key_id", "private_key", 
        "client_email", "client_id", "auth_uri", "token_uri", 
        "auth_provider_x509_cert_url", "client_x509_cert_url"
    ]
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        fixes_applied = []
        
        # Check for required fields
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return None, f"Missing required fields: {', '.join(missing_fields)}"
        
        # Fix private_key formatting issues
        if "private_key" in data:
            private_key = data["private_key"]
            
            # Check for escaped newlines (common issue)
            if "\\n" in private_key and not "\n" in private_key:
                data["private_key"] = private_key.replace("\\n", "\n")
                fixes_applied.append("Replaced escaped newlines in private_key")
            
            # Ensure private key has proper begin/end markers
            if not data["private_key"].startswith("-----BEGIN PRIVATE KEY-----"):
                return None, "Private key is missing proper BEGIN marker"
            
            if not data["private_key"].endswith("-----END PRIVATE KEY-----\n") and not data["private_key"].endswith("-----END PRIVATE KEY-----"):
                return None, "Private key is missing proper END marker"
            
            # Ensure private key has proper newline before END marker
            if "-----END PRIVATE KEY-----" in data["private_key"] and not "\n-----END PRIVATE KEY-----" in data["private_key"]:
                data["private_key"] = data["private_key"].replace("-----END PRIVATE KEY-----", "\n-----END PRIVATE KEY-----")
                fixes_applied.append("Added newline before END marker in private_key")
            
            # Add final newline if missing
            if not data["private_key"].endswith("\n"):
                data["private_key"] += "\n"
                fixes_applied.append("Added final newline to private_key")
        
        # Check client_email format
        if "client_email" in data and not data["client_email"].endswith(".gserviceaccount.com"):
            return None, "Client email does not have the correct format"
        
        message = "No fixes needed" if not fixes_applied else f"Fixes applied: {', '.join(fixes_applied)}"
        
        # Save the fixed data back to the file if requested and fixes were applied
        if save_fixed and fixes_applied:
            try:
                # Create a backup of the original file
                backup_path = f"{file_path}.bak"
                import shutil
                shutil.copy2(file_path, backup_path)
                print(f"📦 Created backup of original file at: {backup_path}")
                
                # Write the fixed data back to the file
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"💾 Saved fixed service account JSON to: {file_path}")
                message += f", saved to file"
            except Exception as e:
                print(f"⚠️ Warning: Could not save fixed data back to file: {str(e)}")
                message += f", but could not save to file: {str(e)}"
        
        return data, message
    
    except json.JSONDecodeError:
        return None, "File is not valid JSON"
    except FileNotFoundError:
        return None, "File not found"
    except Exception as e:
        return None, f"Error processing file: {str(e)}"

def initialize_firebase():
    """
    Initialize Firebase Admin SDK if not already initialized.
    Tries multiple authentication methods in order of preference.
    
    Returns:
        firebase_admin.App: Firebase app instance
    """
    # Project ID for the Firebase project
    project_id = "compliance-d0f59"
    
    # Check if Firebase Admin SDK is already initialized
    if firebase_admin._apps:
        # Use existing app
        firebase_app = firebase_admin.get_app()
        print(f"✅ Firebase Admin SDK already initialized, using existing app")
        return firebase_app
    
    # List of authentication methods to try, in order of preference
    auth_methods = [
        try_render_secret,
        try_env_var,
        try_service_account_file,
        try_application_default
    ]
    
    # Try each authentication method in order
    for method in auth_methods:
        try:
            print(f"🔄 Trying authentication method: {method.__name__}")
            cred = method(project_id)
            if cred:
                # Initialize the Firebase app with the credentials
                firebase_app = firebase_admin.initialize_app(cred)
                print(f"✅ Firebase Admin SDK initialized successfully with {method.__name__}")
                return firebase_app
        except Exception as e:
            print(f"❌ Authentication method {method.__name__} failed: {str(e)}")
    
    # If all methods fail, raise an exception
    raise ValueError("All Firebase authentication methods failed. Please check your credentials.")

def try_render_secret(project_id):
    """Try to authenticate using Render secret file."""
    render_secret_path = "/etc/secrets/firebase_credentials"
    if os.path.exists(render_secret_path):
        try:
            with open(render_secret_path, 'r') as f:
                cred_dict = json.load(f)
            return credentials.Certificate(cred_dict)
        except Exception as e:
            print(f"❌ Error loading Firebase credentials from Render secret file: {str(e)}")
    return None

def try_env_var(project_id):
    """Try to authenticate using environment variable."""
    cred_json = os.getenv("FIREBASE_CREDENTIALS")
    if cred_json:
        try:
            cred_dict = json.loads(cred_json)
            return credentials.Certificate(cred_dict)
        except Exception as e:
            print(f"❌ Error parsing FIREBASE_CREDENTIALS environment variable: {str(e)}")
    return None

def try_service_account_file(project_id):
    """Try to authenticate using service account file."""
    # List of possible paths to the service account file
    possible_paths = [
        "app/auth/firebase-service-account.json",
        "./app/auth/firebase-service-account.json",
        "../app/auth/firebase-service-account.json",
        "backend/app/auth/firebase-service-account.json"
    ]
    
    # Add path with full resolution
    base_dir = pathlib.Path(__file__).parent.parent.parent.parent
    possible_paths.append(str(base_dir / "backend" / "app" / "auth" / "firebase-service-account.json"))
    
    # Try each path
    for path in possible_paths:
        if os.path.exists(path):
            print(f"📄 Found credentials file at: {path}")
            
            # Try to fix any issues with the service account JSON
            fixed_data, fix_message = fix_service_account_json(path, save_fixed=True)
            
            if fixed_data:
                print(f"🔧 Service account JSON processing: {fix_message}")
                try:
                    # Create credentials from the fixed JSON data
                    return credentials.Certificate(fixed_data)
                except Exception as e:
                    print(f"❌ Error using fixed credentials data: {str(e)}")
                    
                    # As a last resort, try using the file path directly
                    try:
                        print("⚠️ Attempting to use file path directly as fallback...")
                        return credentials.Certificate(path)
                    except Exception as e2:
                        print(f"❌ Error using credentials file directly: {str(e2)}")
            else:
                print(f"❌ Could not fix service account JSON: {fix_message}")
    
    return None

def try_application_default(project_id):
    """Try to authenticate using Application Default Credentials."""
    try:
        # Use Application Default Credentials
        cred = credentials.ApplicationDefault()
        print(f"✅ Using Application Default Credentials")
        return cred
    except Exception as e:
        print(f"❌ Error using Application Default Credentials: {str(e)}")
        return None

# Initialize Firebase when this module is imported
try:
    firebase_app = initialize_firebase()
except Exception as e:
    print(f"❌ Error initializing Firebase: {str(e)}")
    # Don't re-raise the exception to allow the application to start
    # even if Firebase initialization fails
    firebase_app = None
