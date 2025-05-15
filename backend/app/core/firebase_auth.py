import firebase_admin
from firebase_admin import auth
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Import the centralized Firebase initialization
from app.core.firebase_init import firebase_app

# Security scheme for Firebase token
security = HTTPBearer()

async def get_current_firebase_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify Firebase ID token and return user information
    """
    print(f"[DEBUG] Received credentials: {credentials}")

    if not credentials:
        print(f"[ERROR] No credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication credentials provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    print(f"[DEBUG] Received token: {token[:20]}...")

    try:
        # Verify the token
        print(f"[DEBUG] Verifying token with Firebase...")

        # Check if token is empty or malformed
        if not token or len(token) < 50:  # Firebase tokens are typically long
            print(f"[ERROR] Token appears to be invalid or too short: {token[:20]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Add more detailed error handling for token verification
        try:
            decoded_token = auth.verify_id_token(token)
            print(f"[DEBUG] Token verified successfully. Decoded token: {decoded_token}")
        except auth.InvalidIdTokenError:
            print(f"[ERROR] Invalid ID token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid ID token. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except auth.ExpiredIdTokenError:
            print(f"[ERROR] Expired ID token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except auth.RevokedIdTokenError:
            print(f"[ERROR] Revoked ID token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except auth.CertificateFetchError:
            print(f"[ERROR] Certificate fetch error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify token due to certificate fetch error.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user information
        user_id = decoded_token.get("uid")
        email = decoded_token.get("email", "")
        name = decoded_token.get("name", "")
        picture = decoded_token.get("picture", "")

        print(f"[DEBUG] User info - ID: {user_id}, Email: {email}")

        # Return user data
        return {
            "id": user_id,
            "email": email,
            "username": email,  # Use email as username for compatibility
            "full_name": name,
            "picture": picture
        }
    except Exception as e:
        print(f"[ERROR] Firebase token verification failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Compatibility function to work with existing code
def get_current_user_compatibility(firebase_user: dict = Depends(get_current_firebase_user)):
    """
    Provides compatibility with existing code that uses the JWT-based authentication
    """
    # Convert Firebase user format to match the existing JWT user format
    return {
        "id": firebase_user["id"],
        "username": firebase_user["username"],
        "email": firebase_user["email"],
        "full_name": firebase_user["full_name"]
    }
