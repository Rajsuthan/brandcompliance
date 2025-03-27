# Backend Setup Guide

This guide explains how to set up the backend and run the image and video agents.

## Setup Instructions

1. Install dependencies:

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the `backend` directory with your API keys:

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

   # Auth settings
   SECRET_KEY="your-secret-key-here"
   ALGORITHM="HS256"
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

## Testing the Image Agent

The image agent is integrated with the API and can be tested in two ways:

### Method 1: Using the API Server

1. Start the API server:

   ```bash
   cd backend
   python main.py
   ```

2. Access the API at `http://localhost:8000`

3. Use the frontend application to interact with the API, or test directly using the Swagger UI at `http://localhost:8000/docs`

### Method 2: Using the Test Script

Run the test script to check image compliance:

```bash
cd backend
python test_compliance_api.py
```

## Running the Video Agent

The video agent runs as a standalone script:

```bash
cd backend
python -m app.core.video_agent.llm
```

To analyze a different video, modify the `video_url` variable in `app/core/video_agent/llm.py`:

```python
# In app/core/video_agent/llm.py (around line 330)
video_url = "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"  # Change this URL
```
