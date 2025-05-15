import pytest
import json
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

# Import the main FastAPI app
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from main import app
from app.core.firebase_auth import get_current_firebase_user

# Create test client
client = TestClient(app)

# Sample Firebase ID token payload
SAMPLE_FIREBASE_PAYLOAD = {
    "uid": "test-user-123",
    "email": "test@example.com",
    "name": "Test User",
    "picture": "https://example.com/profile.jpg",
    "email_verified": True
}

# Mock Firebase token verification
@pytest.fixture
def mock_firebase_verify():
    with patch('firebase_admin.auth.verify_id_token') as mock:
        mock.return_value = SAMPLE_FIREBASE_PAYLOAD
        yield mock

# Test the Firebase token verification endpoint
def test_verify_token_endpoint(mock_firebase_verify):
    response = client.post(
        "/api/firebase-auth/verify-token",
        headers={"Authorization": "Bearer fake-token"}
    )
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["user"]["id"] == SAMPLE_FIREBASE_PAYLOAD["uid"]
    assert data["user"]["email"] == SAMPLE_FIREBASE_PAYLOAD["email"]
    
    # Verify the mock was called with the correct token
    mock_firebase_verify.assert_called_once_with("fake-token")

# Test the current user endpoint
def test_get_current_user_endpoint(mock_firebase_verify):
    response = client.get(
        "/api/firebase-auth/me",
        headers={"Authorization": "Bearer fake-token"}
    )
    
    # Check response
    assert response.status_code == 200
    user = response.json()
    assert user["id"] == SAMPLE_FIREBASE_PAYLOAD["uid"]
    assert user["email"] == SAMPLE_FIREBASE_PAYLOAD["email"]
    assert user["full_name"] == SAMPLE_FIREBASE_PAYLOAD["name"]
    assert user["picture"] == SAMPLE_FIREBASE_PAYLOAD["picture"]

# Test the get_current_firebase_user function directly
@pytest.mark.asyncio
async def test_get_current_firebase_user(mock_firebase_verify):
    # Create mock credentials
    mock_credentials = MagicMock()
    mock_credentials.credentials = "fake-token"
    
    # Call the function
    user = await get_current_firebase_user(mock_credentials)
    
    # Check the result
    assert user["id"] == SAMPLE_FIREBASE_PAYLOAD["uid"]
    assert user["email"] == SAMPLE_FIREBASE_PAYLOAD["email"]
    assert user["username"] == SAMPLE_FIREBASE_PAYLOAD["email"]
    assert user["full_name"] == SAMPLE_FIREBASE_PAYLOAD["name"]
    assert user["picture"] == SAMPLE_FIREBASE_PAYLOAD["picture"]

# Test invalid token handling
@pytest.mark.asyncio
async def test_invalid_token_handling():
    # Mock Firebase auth to raise an exception
    with patch('firebase_admin.auth.verify_id_token') as mock:
        mock.side_effect = Exception("Invalid token")
        
        # Create mock credentials
        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid-token"
        
        # Call the function and expect an exception
        with pytest.raises(HTTPException) as excinfo:
            await get_current_firebase_user(mock_credentials)
        
        # Check the exception
        assert excinfo.value.status_code == 401
        assert "Invalid authentication credentials" in excinfo.value.detail

# Test the user profile endpoint
def test_user_profile_endpoint(mock_firebase_verify):
    response = client.get(
        "/api/user/profile",
        headers={"Authorization": "Bearer fake-token"}
    )
    
    # Check response
    assert response.status_code == 200
    user = response.json()
    assert user["id"] == SAMPLE_FIREBASE_PAYLOAD["uid"]
    assert user["email"] == SAMPLE_FIREBASE_PAYLOAD["email"]

# Integration test for email/password authentication
# Note: This requires actual Firebase credentials and cannot be fully mocked
@pytest.mark.skip(reason="Requires actual Firebase credentials")
def test_email_password_auth_integration():
    from firebase_admin import auth
    
    # Test user credentials
    email = "test_user@example.com"
    password = "Test@123456"
    
    try:
        # Try to create a test user (may fail if user already exists)
        user = auth.create_user(
            email=email,
            password=password,
            display_name="Test User"
        )
        print(f"Created test user with UID: {user.uid}")
    except Exception as e:
        print(f"User creation error (may already exist): {e}")
    
    # Get a custom token for the test user
    # Note: In a real scenario, the client would use Firebase client SDK to sign in
    # and get an ID token. This is just for testing the backend verification.
    try:
        # Get user by email
        user = auth.get_user_by_email(email)
        custom_token = auth.create_custom_token(user.uid)
        
        # Use the token to verify with our backend
        response = client.post(
            "/api/firebase-auth/verify-token",
            headers={"Authorization": f"Bearer {custom_token.decode('utf-8')}"}
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "user" in data
    except Exception as e:
        pytest.fail(f"Integration test failed: {e}")

if __name__ == "__main__":
    # Run the tests
    pytest.main(["-xvs", __file__])
