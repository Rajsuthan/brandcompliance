# Compliance Project Backend

This is the backend service for the Compliance Project, which provides AI-powered compliance checking for images and videos against brand guidelines.

## Features

- Image compliance checking against brand guidelines
- Video compliance checking against brand guidelines
- Font detection
- Color scheme analysis
- Layout consistency checking
- Element placement analysis

## Prerequisites

- Python 3.9+
- MongoDB
- API keys for various services (Google, OpenAI, Anthropic, WhatFontIs)

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd compliance-proj/backend
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Setup

The application uses a `.env` file to manage environment variables and API keys. Create a `.env` file in the `backend` directory with the following content:

```
# API Keys
GOOGLE_API_KEY="your-google-api-key"
AZURE_API_KEY="your-azure-api-key"
AZURE_ENDPOINT="your-azure-endpoint"
OPENAI_API_KEY="your-openai-api-key"
ANTHROPIC_API_KEY="your-anthropic-api-key"
WHATFONTIS_API_KEY="your-whatfontis-api-key"

# Google Cloud Settings
GOOGLE_CLOUD_PROJECT="your-google-cloud-project-id"
GOOGLE_CLOUD_LOCATION="your-google-cloud-location"

# Firebase Settings (IMPORTANT - use one of these methods)
# Option 1: Set the JSON content directly (recommended for production)
FIREBASE_CREDENTIALS='{"type":"service_account","project_id":"your-project-id","private_key_id":"your-private-key-id","private_key":"-----BEGIN PRIVATE KEY-----\\nYour private key here\\n-----END PRIVATE KEY-----\\n","client_email":"your-service-account-email@your-project-id.iam.gserviceaccount.com","client_id":"your-client-id","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/your-service-account-email%40your-project-id.iam.gserviceaccount.com","universe_domain":"googleapis.com"}'

# Option 2: Set the path to your service account file (for development)
FIREBASE_CREDENTIALS_PATH="app/auth/firebase-service-account.json"

# Auth settings
SECRET_KEY="your-secret-key-here"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Replace the placeholder values with your actual API keys and configuration.

## Firebase Setup

This application uses Firebase for authentication and Firestore for data storage. To set up Firebase:

1. Create a Firebase project at [https://console.firebase.google.com/](https://console.firebase.google.com/)

2. Generate a service account key:

   - Go to Project Settings > Service Accounts
   - Click "Generate new private key"
   - Save the JSON file securely

3. Configure Firebase credentials using one of these methods:

   **Method 1: Environment Variable (Recommended for production)**

   - Set the `FIREBASE_CREDENTIALS` environment variable with the entire JSON content of your service account key
   - Make sure to escape newlines in the private key with `\\n`

   **Method 2: JSON File (Easier for development)**

   - Save your service account key as `backend/app/auth/firebase-service-account.json`
   - Set `FIREBASE_CREDENTIALS_PATH` in your `.env` file to point to this file
   - **IMPORTANT**: Never commit this file to version control!
   - Add it to your `.gitignore` file

4. Enable Authentication methods in the Firebase Console:

   - Go to Authentication > Sign-in method
   - Enable Email/Password and Google authentication methods

5. Set up Firestore database:
   - Go to Firestore Database
   - Create a database in production mode
   - Choose a location close to your users

## Running the Application

### Start the API Server

To start the main API server:

```bash
cd backend
python main.py
```

The API will be available at `http://localhost:8000`.

### API Documentation

Once the server is running, you can access the API documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testing the Image Agent

The image agent can be tested using the provided test script:

```bash
python test_compliance_api.py
```

This script will:

1. Create a test user (if needed)
2. Log in to get an authentication token
3. Upload a test image for compliance checking
4. Display the compliance results

You can also test the image agent tools directly:

```bash
python test_compliance_tools.py
```

This will test individual tools like color scheme analysis, font detection, etc.

## Testing the Video Agent

Unlike the image agent which is integrated with the API and frontend, the video agent needs to be run directly as a standalone script:

```bash
# Run the video agent directly
python -m app.core.video_agent.llm
```

This will:

1. Download a sample YouTube video (default: https://www.youtube.com/watch?v=9cPxh2DikIA)
2. Extract frames at regular intervals
3. Analyze the frames for brand compliance
4. Generate a compliance report

To analyze a different video, modify the `video_url` variable in the `app/core/video_agent/llm.py` file:

```python
# In app/core/video_agent/llm.py
video_url = "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"  # Change this URL
```

## Project Structure

- `app/`: Main application code
  - `api/`: API endpoints
  - `core/`: Core business logic
    - `agent/`: Image compliance agent
    - `video_agent/`: Video compliance agent
  - `db/`: Database models and connections
  - `models/`: Pydantic models
  - `utils/`: Utility functions

## Troubleshooting

### API Key Issues

If you encounter errors related to API keys, ensure that:

1. All required keys are properly set in the `.env` file
2. The keys have the necessary permissions
3. The services are available and not experiencing downtime

### MongoDB Connection Issues

If you have trouble connecting to MongoDB:

1. Ensure MongoDB is running
2. Check the connection string in `app/db/database.py`
3. Verify network connectivity to the MongoDB server

### Video Processing Issues

If video processing fails:

1. Ensure you have sufficient disk space for temporary video files
2. Check that the video URL is accessible
3. Verify that all required Python packages are installed (opencv-python, yt-dlp)

### Firebase Authentication Issues

If you encounter Firebase authentication issues:

1. Check that your Firebase service account credentials are correctly configured
2. Verify that the Firebase project has Authentication enabled
3. Ensure that the service account has the necessary permissions
4. Check that the Firestore database is created and accessible
5. If using environment variables, ensure the JSON is properly formatted with escaped newlines

### Security Best Practices

To maintain security of your Firebase credentials:

1. Never commit service account keys to version control
2. Use environment variables in production environments
3. Regularly rotate service account keys
4. Limit the permissions of your service account to only what's needed
5. Monitor your Firebase project for unusual activity

## License

[License information]
