# How to Regenerate Firebase Service Account Key

The current Firebase service account key appears to have an issue with its JWT signature. To fix this, you'll need to regenerate the service account key in the Firebase console and replace the existing one.

## Steps to Regenerate the Service Account Key

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Select your project: `compliance-d0f59`
3. Click on the gear icon (⚙️) next to "Project Overview" to open Project settings
4. Go to the "Service accounts" tab
5. Click on "Generate new private key" button
6. Save the downloaded JSON file
7. Replace the existing service account file at `backend/app/auth/firebase-service-account.json` with this new file

## After Regenerating the Key

After replacing the service account file, run the test script again to verify the connection:

```bash
cd backend
python test_firebase_connection.py
```

If the test passes, update your application to use the new service account key.

## Alternative: Use Environment Variables

If you continue to have issues with the service account file, consider using environment variables instead:

1. Set the `FIREBASE_CREDENTIALS` environment variable with the entire JSON content of your service account key
2. Make sure to escape newlines in the private key with `\\n`

Example:

```bash
export FIREBASE_CREDENTIALS='{"type":"service_account","project_id":"compliance-d0f59",...}'
```

Or add it to your `.env` file:

```
FIREBASE_CREDENTIALS={"type":"service_account","project_id":"compliance-d0f59",...}
```

The Firebase initialization code is already set up to use this environment variable if available.
