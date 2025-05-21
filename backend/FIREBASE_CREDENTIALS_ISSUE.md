# Firebase Credentials Issue

## Problem

We're encountering an "Invalid JWT Signature" error when trying to connect to Firebase Firestore. This suggests there's an issue with the service account key file.

## Diagnosis

1. The Firebase initialization appears to work, but when trying to access Firestore, we get an "Invalid JWT Signature" error.
2. We've tried:
   - Using the service account file directly
   - Parsing and fixing the JSON file
   - Converting the credentials to an environment variable

## Solution

The most reliable solution is to generate a new service account key from the Firebase console:

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Select your project: `compliance-d0f59`
3. Click on the gear icon (⚙️) next to "Project Overview" to open Project settings
4. Go to the "Service accounts" tab
5. Click on "Generate new private key" button
6. Save the downloaded JSON file
7. Replace the existing service account file at `backend/app/auth/firebase-service-account.json` with this new file

## Alternative Solutions

If generating a new key is not possible, try these alternatives:

### 1. Use Google Application Default Credentials

1. Install the Google Cloud SDK
2. Run `gcloud auth application-default login`
3. Update the Firebase initialization code to use application default credentials:

```python
import firebase_admin
from firebase_admin import credentials

# Use application default credentials
cred = credentials.ApplicationDefault()
firebase_app = firebase_admin.initialize_app(cred, {
    'projectId': 'compliance-d0f59',
})
```

### 2. Use a Different Service Account

If you have access to other service accounts for the same project, try using one of those instead.

### 3. Check Time Synchronization

Ensure that your system clock is correctly synchronized, as JWT validation is time-sensitive.

## Next Steps

After implementing one of these solutions, test the connection again using:

```bash
python test_firebase_connection.py
```

If the issue persists, please contact Firebase support with the detailed error messages.
