# Firebase Connection - Final Solution

## Problem Summary

We're encountering an "Invalid JWT Signature" error when trying to connect to Firebase Firestore. This is a common issue that can occur for several reasons:

1. The service account private key is malformed or corrupted
2. The service account has been revoked or disabled
3. The system clock is not synchronized correctly
4. The service account doesn't have the necessary permissions

## Solutions Implemented

We've implemented several solutions to address this issue:

1. **Enhanced Firebase Initialization**: We've improved the Firebase initialization code to handle multiple authentication methods and provide better error handling.

2. **Service Account JSON Fixing**: We've created utilities to fix common issues with service account JSON files, such as escaped newlines in the private key.

3. **Environment Variable Approach**: We've set up a way to use Firebase credentials from environment variables, which can be more reliable than file-based credentials.

4. **Application Default Credentials**: We've added support for using Google Application Default Credentials as a fallback.

## Recommended Next Steps

Since we're still encountering the "Invalid JWT Signature" error despite our fixes, here are the recommended next steps:

### 1. Generate a New Service Account Key (Highest Priority)

The most reliable solution is to generate a new service account key:

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Select your project: `compliance-d0f59`
3. Click on the gear icon (⚙️) next to "Project Overview" to open Project settings
4. Go to the "Service accounts" tab
5. Click on "Generate new private key" button
6. Save the downloaded JSON file
7. Replace the existing service account file at `backend/app/auth/firebase-service-account.json` with this new file

### 2. Check System Clock Synchronization

JWT validation is time-sensitive, so ensure your system clock is correctly synchronized:

```bash
# On macOS/Linux
date

# On Windows
time /t
```

If the time is incorrect, synchronize it:

```bash
# On macOS/Linux
sudo ntpdate -u time.google.com

# On Windows
w32tm /resync
```

### 3. Use a Different Authentication Method

If generating a new key is not possible, try one of these alternatives:

#### a. Use Google Application Default Credentials

1. Install the Google Cloud SDK
2. Run:
   ```bash
   gcloud auth application-default login
   gcloud config set project compliance-d0f59
   ```

3. Update the Firebase initialization code to use Application Default Credentials:
   ```python
   cred = credentials.ApplicationDefault()
   firebase_app = firebase_admin.initialize_app(cred, {
       'projectId': 'compliance-d0f59',
   })
   ```

#### b. Use a Different Service Account

If you have access to other service accounts for the same project, try using one of those instead.

## Implementation Files

We've created several files to help with this issue:

1. `app/core/firebase_init_new.py`: A new implementation of the Firebase initialization code that supports multiple authentication methods.

2. `fix_private_key.py`: A script to fix formatting issues in the private key.

3. `setup_firebase_env.py`: A script to set up Firebase credentials as an environment variable.

4. `test_firebase_connection.py`: A script to test the Firebase connection.

5. `test_new_firebase_init.py`: A script to test the new Firebase initialization implementation.

## Deployment Considerations

When deploying your application, consider these options:

1. **Environment Variables**: Set the `FIREBASE_CREDENTIALS` environment variable with the entire JSON content of your service account key.

2. **Secret Management**: Use a secret management service like Render's secret files to store your Firebase credentials securely.

3. **Application Default Credentials**: Configure your deployment environment to use Application Default Credentials.

## Conclusion

The "Invalid JWT Signature" error is likely due to an issue with the service account key itself, rather than how it's being loaded. Generating a new service account key is the most reliable solution to this problem.

If you continue to have issues after trying these solutions, please contact Firebase support with the detailed error messages.
