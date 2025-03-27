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

# Auth settings
SECRET_KEY="your-secret-key-here"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Replace the placeholder values with your actual API keys and configuration.

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

## License

[License information]
