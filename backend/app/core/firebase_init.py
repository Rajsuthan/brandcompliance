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
            # First try to load from Render secret file (preferred method for production)
            render_secret_path = "/etc/secrets/compliance-d0f59-firebase-adminsdk-fbsvc-dfc358517f.json"
            if os.path.exists(render_secret_path):
                try:
                    with open(render_secret_path, 'r') as f:
                        cred_dict = json.load(f)
                    cred = credentials.Certificate(cred_dict)
                    print(f"✅ Using Firebase credentials from Render secret file")
                except Exception as e:
                    print(f"❌ Error loading Firebase credentials from Render secret file: {str(e)}")
                    raise ValueError(f"Failed to load Firebase credentials from Render secret file: {str(e)}")
            else:
                # Fallback to environment variable
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
                    cred_path = "app/auth/compliance-d0f59-firebase-adminsdk-fbsvc-dfc358517f.json"

                    # Try to fix and load the service account JSON
                    if os.path.exists(cred_path):
                        print(f"📄 Found credentials file at: {cred_path}")

                        # First try to fix any issues with the service account JSON and save the fixes
                        fixed_data, fix_message = fix_service_account_json(cred_path, save_fixed=True)

                        if fixed_data:
                            print(f"🔧 Service account JSON processing: {fix_message}")

                            try:
                                # Create credentials from the fixed JSON data
                                cred = credentials.Certificate(fixed_data)
                                print(f"✅ Using Firebase credentials from fixed JSON data")
                            except Exception as e:
                                print(f"❌ Error using fixed credentials data: {str(e)}")

                                # As a last resort, try using the file path directly
                                try:
                                    print("⚠️ Attempting to use file path directly as fallback...")
                                    cred = credentials.Certificate(cred_path)
                                    print(f"✅ Using Firebase credentials from file path directly: {cred_path}")
                                except Exception as e2:
                                    print(f"❌ Error using credentials file directly: {str(e2)}")
                                    raise ValueError(f"Failed to initialize Firebase credentials: {str(e)} / {str(e2)}")
                        else:
                            print(f"❌ Could not fix service account JSON: {fix_message}")
                            raise ValueError(f"Invalid service account JSON: {fix_message}")
                    else:
                        # Try alternative path with full path resolution
                        import pathlib
                        base_dir = pathlib.Path(__file__).parent.parent.parent.parent
                        alt_cred_path = base_dir / "backend" / "app" / "auth" / "compliance-d0f59-firebase-adminsdk-fbsvc-dfc358517f.json"

                        if os.path.exists(alt_cred_path):
                            print(f"📄 Found credentials file at alternative path: {alt_cred_path}")

                            # First try to fix any issues with the service account JSON and save the fixes
                            fixed_data, fix_message = fix_service_account_json(str(alt_cred_path), save_fixed=True)

                            if fixed_data:
                                print(f"🔧 Service account JSON processing: {fix_message}")

                                try:
                                    # Create credentials from the fixed JSON data
                                    cred = credentials.Certificate(fixed_data)
                                    print(f"✅ Using Firebase credentials from fixed JSON data (alternative path)")
                                except Exception as e:
                                    print(f"❌ Error using fixed credentials data: {str(e)}")

                                    # As a last resort, try using the file path directly
                                    try:
                                        print("⚠️ Attempting to use file path directly as fallback...")
                                        cred = credentials.Certificate(str(alt_cred_path))
                                        print(f"✅ Using Firebase credentials from file path directly: {alt_cred_path}")
                                    except Exception as e2:
                                        print(f"❌ Error using credentials file directly: {str(e2)}")
                                        raise ValueError(f"Failed to initialize Firebase credentials: {str(e)} / {str(e2)}")
                            else:
                                print(f"❌ Could not fix service account JSON: {fix_message}")
                                raise ValueError(f"Invalid service account JSON: {fix_message}")
                        else:
                            raise ValueError("Firebase credentials not found. Please provide credentials via Render secret file, environment variable, or local file at app/auth/compliance-d0f59-firebase-adminsdk-fbsvc-dfc358517f.json")

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

# Function to fix service account JSON file
def fix_firebase_credentials(file_path=None):
    """
    Fix the Firebase service account JSON file.

    Args:
        file_path: Path to the service account JSON file. If None, uses the default path.

    Returns:
        bool: True if successful, False otherwise
    """
    if file_path is None:
        # Try default paths
        default_paths = [
            "app/auth/compliance-d0f59-firebase-adminsdk-fbsvc-dfc358517f.json",
            "backend/app/auth/compliance-d0f59-firebase-adminsdk-fbsvc-dfc358517f.json"
        ]

        # Add path with full resolution
        import pathlib
        base_dir = pathlib.Path(__file__).parent.parent.parent.parent
        default_paths.append(str(base_dir / "backend" / "app" / "auth" / "compliance-d0f59-firebase-adminsdk-fbsvc-dfc358517f.json"))

        # Try each path
        for path in default_paths:
            if os.path.exists(path):
                file_path = path
                break

        if file_path is None:
            print(f"❌ Could not find service account JSON file in any of the default paths")
            return False

    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False

    print(f"📄 Found service account JSON file: {file_path}")
    fixed_data, message = fix_service_account_json(file_path, save_fixed=True)

    if fixed_data:
        print(f"✅ Successfully processed service account JSON: {message}")
        return True
    else:
        print(f"❌ Failed to fix service account JSON: {message}")
        return False

# Initialize Firebase when this module is imported
firebase_app = initialize_firebase()
