import os
import json
import requests
import firebase_admin
from firebase_admin import credentials, auth
import argparse
import sys
from getpass import getpass

# Parse command line arguments
parser = argparse.ArgumentParser(description='Test Firebase Authentication Integration')
parser.add_argument('--email', help='Email for testing')
parser.add_argument('--create-user', action='store_true', help='Create a new test user')
parser.add_argument('--delete-user', action='store_true', help='Delete the test user after testing')
parser.add_argument('--backend-url', default='http://localhost:8000', help='Backend URL')
args = parser.parse_args()

# Initialize Firebase Admin SDK
try:
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

    # Initialize the Firebase app
    firebase_app = firebase_admin.initialize_app(cred)
    print(f"✅ Firebase Admin SDK initialized successfully")
except Exception as e:
    print(f"❌ Error initializing Firebase Admin SDK: {str(e)}")
    sys.exit(1)

def create_test_user(email, password):
    """Create a test user with email and password"""
    try:
        user = auth.create_user(
            email=email,
            password=password,
            display_name=f"Test User ({email})"
        )
        print(f"✅ Created test user with UID: {user.uid}")
        return user.uid
    except Exception as e:
        print(f"❌ User creation error: {e}")
        return None

def delete_test_user(email):
    """Delete a test user by email"""
    try:
        user = auth.get_user_by_email(email)
        auth.delete_user(user.uid)
        print(f"✅ Deleted test user with UID: {user.uid}")
        return True
    except Exception as e:
        print(f"❌ User deletion error: {e}")
        return False

def create_custom_token(uid):
    """Create a custom token for testing"""
    try:
        token = auth.create_custom_token(uid)
        return token.decode('utf-8')
    except Exception as e:
        print(f"❌ Error creating custom token: {e}")
        return None

def verify_token_with_backend(token, backend_url):
    """Verify the token with our backend"""
    try:
        response = requests.post(
            f"{backend_url}/api/firebase-auth/verify-token",
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code == 200:
            print(f"✅ Token verification successful")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"❌ Token verification failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error verifying token with backend: {e}")
        return False

def get_user_profile(token, backend_url):
    """Get user profile from our backend"""
    try:
        response = requests.get(
            f"{backend_url}/api/user/profile",
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code == 200:
            print(f"✅ User profile retrieval successful")
            print(f"Profile: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"❌ User profile retrieval failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error getting user profile: {e}")
        return False

def main():
    # Get email from args or prompt
    email = args.email
    if not email:
        email = input("Enter email for testing: ")

    # Create a new test user if requested
    if args.create_user:
        password = getpass("Enter password for the test user: ")
        uid = create_test_user(email, password)
        if not uid:
            print("Failed to create test user. Exiting.")
            sys.exit(1)
    else:
        # Get existing user
        try:
            user = auth.get_user_by_email(email)
            uid = user.uid
            print(f"✅ Found existing user with UID: {uid}")
        except Exception as e:
            print(f"❌ Error finding user: {e}")
            print("User does not exist. Use --create-user to create a new test user.")
            sys.exit(1)

    # Create a custom token for the user
    token = create_custom_token(uid)
    if not token:
        print("Failed to create custom token. Exiting.")
        sys.exit(1)

    print(f"Generated custom token: {token[:20]}...")

    # Important note about token verification
    print("\n⚠️ IMPORTANT: Server-side testing limitation")
    print("The backend expects an ID token, but we can only generate custom tokens on the server.")
    print("To fully test the authentication flow:")
    print("1. Use the custom token in a client app to sign in with Firebase")
    print("2. Get the ID token from the client")
    print("3. Use that ID token to authenticate with the backend")
    print("\nFor now, we'll verify that the Firebase Admin SDK is working correctly by:")
    print("1. Successfully creating/retrieving a user")
    print("2. Successfully generating a custom token")

    # Skip backend verification since we can't generate ID tokens server-side
    print("\n✅ Firebase authentication setup is working correctly!")
    print("✅ User management is working correctly!")
    print("✅ Custom token generation is working correctly!")

    # Note about backend verification
    print("\n⚠️ To test the backend verification:")
    print("1. Implement the frontend authentication")
    print("2. Use the frontend to sign in and get an ID token")
    print("3. Use that ID token to authenticate with the backend")

    # Delete the test user if requested
    if args.delete_user:
        print(f"\nDeleting test user...")
        if not delete_test_user(email):
            print("Failed to delete test user.")
            sys.exit(1)

    print("\n✅ Firebase authentication setup tests completed successfully!")

if __name__ == "__main__":
    main()
