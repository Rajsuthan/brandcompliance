import os
from dotenv import load_dotenv
from pymongo import MongoClient
import sys

# Load environment variables from .env file
load_dotenv()

# Get MongoDB connection details from environment variables
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("MONGODB_DB_NAME")

print(f"Attempting to connect to MongoDB...")
print(f"MongoDB URI: {MONGODB_URI}")
print(f"Database Name: {DB_NAME}")

try:
    # Create a MongoDB client
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)

    # Force a connection to verify it works
    client.admin.command("ping")

    print("✅ Successfully connected to MongoDB!")

    # Try to access the database
    db = client[DB_NAME]
    print(f"✅ Successfully accessed database: {DB_NAME}")

    # List collections in the database
    collections = db.list_collection_names()
    print(f"Collections in {DB_NAME}: {collections}")

    # Check if brand_guidelines collection exists
    if "brand_guidelines" in collections:
        print("✅ brand_guidelines collection exists")

        # Count documents in brand_guidelines collection
        count = db.brand_guidelines.count_documents({})
        print(f"Number of documents in brand_guidelines collection: {count}")

        # Get one document from brand_guidelines collection
        if count > 0:
            doc = db.brand_guidelines.find_one()
            print(f"Sample document: {doc}")
    else:
        print("❌ brand_guidelines collection does not exist")

except Exception as e:
    print(f"❌ Error connecting to MongoDB: {e}")
    sys.exit(1)

print("MongoDB connection test completed.")
