from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from app.core.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.models.user import User, UserCreate, Token, LoginRequest
from app.db.database import users_collection as users_collection_mongo
from app.db.firestore import users_collection
from bson import ObjectId

router = APIRouter()


@router.post("/signup", response_model=User)
async def signup(user: UserCreate):
    try:
        # Check if user already exists in Firestore
        query = users_collection.where('username', '==', user.username).limit(1)
        existing_users = list(query.stream())

        if existing_users:
            raise HTTPException(status_code=400, detail="Username already registered")

        # Create new user
        hashed_password = get_password_hash(user.password)
        user_data = user.model_dump()
        user_data.pop("password")
        user_data["hashed_password"] = hashed_password

        # Add timestamps
        from firebase_admin import firestore
        user_data['created_at'] = firestore.SERVER_TIMESTAMP

        # Create user in Firestore
        doc_ref = users_collection.document()
        doc_ref.set(user_data)
        user_data["id"] = doc_ref.id

        print(f"[INFO] Created user in Firestore with ID: {doc_ref.id}")
        return user_data
    except Exception as e:
        print(f"[WARNING] Failed to create user in Firestore: {str(e)}")

        # Fallback to MongoDB
        try:
            # Check if user already exists in MongoDB
            db_user = users_collection_mongo.find_one({"username": user.username})
            if db_user:
                raise HTTPException(status_code=400, detail="Username already registered")

            # Create new user in MongoDB
            hashed_password = get_password_hash(user.password)
            user_data = user.model_dump()
            user_data.pop("password")
            user_data["hashed_password"] = hashed_password

            result = users_collection_mongo.insert_one(user_data)
            user_data["id"] = str(result.inserted_id)

            print(f"[INFO] Created user in MongoDB with ID: {result.inserted_id}")
            return user_data
        except HTTPException:
            raise
        except Exception as e2:
            print(f"[ERROR] Failed to create user in MongoDB: {str(e2)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user: {str(e2)}"
            )


@router.post("/token", response_model=Token)
async def login_for_access_token(login_data: LoginRequest):
    user = authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=User)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
