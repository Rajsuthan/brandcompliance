# Firebase Connection Solution

We've improved the Firebase connection initialization to use the service account JSON from the app/auth directory. However, we're still encountering an "Invalid JWT Signature" error when trying to connect to Firestore.

## What We've Done

1. Enhanced the Firebase initialization code to:
   - Properly load and parse the service account JSON file
   - Fix common issues with the private key format
   - Add detailed error logging
   - Provide multiple fallback mechanisms

2. Created several utility scripts:
   - `fix_private_key.py`: Fixes formatting issues in the private key
   - `setup_firebase_env.py`: Sets up Firebase credentials as an environment variable
   - `test_firebase_connection.py`: Tests the Firebase connection
   - `use_application_default_credentials.py`: Tests using Google Application Default Credentials

## Recommended Solutions (in order of preference)

### 1. Generate a New Service Account Key (Recommended)

The most reliable solution is to generate a new service account key:

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Select your project: `compliance-d0f59`
3. Click on the gear icon (⚙️) next to "Project Overview" to open Project settings
4. Go to the "Service accounts" tab
5. Click on "Generate new private key" button
6. Save the downloaded JSON file
7. Replace the existing service account file at `backend/app/auth/firebase-service-account.json` with this new file

### 2. Use Environment Variables

If generating a new key is not immediately possible, try using environment variables:

1. Run the setup script:
   ```bash
   cd backend
   python setup_firebase_env.py
   ```

2. Source the environment file:
   ```bash
   source .env.firebase
   ```

3. Test the connection:
   ```bash
   python test_firebase_connection.py
   ```

### 3. Use Google Application Default Credentials

As a last resort, you can use Google Application Default Credentials:

1. Install the Google Cloud SDK
2. Run:
   ```bash
   gcloud auth application-default login
   gcloud config set project compliance-d0f59
   ```

3. Test with:
   ```bash
   cd backend
   python use_application_default_credentials.py
   ```

4. If successful, update your code as instructed by the script.

## Troubleshooting

If you continue to have issues:

1. Check that your system clock is correctly synchronized (JWT validation is time-sensitive)
2. Verify that the service account has the necessary permissions in Firebase
3. Check if the service account has been disabled or revoked
4. Try using a different service account for the same project
5. Contact Firebase support with the detailed error messages

## Next Steps

After implementing one of these solutions and confirming it works, make sure to update any deployment configurations to use the same approach.
