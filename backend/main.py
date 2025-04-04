from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api import auth, items, brand_guidelines, compliance, video_upload

# Initialize FastAPI app
app = FastAPI(
    title="Compliance API", description="API for compliance management", version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the Compliance API"}


# Include routers
app.include_router(auth.router, tags=["authentication"])
app.include_router(items.router, prefix="/api", tags=["items"])
app.include_router(brand_guidelines.router, prefix="/api", tags=["brand-guidelines"])
app.include_router(compliance.router, prefix="/api", tags=["compliance"])
app.include_router(
    video_upload.router, prefix="/api", tags=["Video Upload"]
)  # Added video upload router

# Run the application
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
