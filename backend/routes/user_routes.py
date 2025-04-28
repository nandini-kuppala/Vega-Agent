from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from datetime import datetime, timedelta
import bcrypt
import jwt
from pydantic import BaseModel

from models.user_model import UserCreate, UserResponse, UserInDB
from database import users_collection

router = APIRouter()

# Secret key for JWT
SECRET_KEY = "asha_ai_secret_key"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post("/signup", response_model=Token)
async def create_user(user: UserCreate):
    # Check if user with this email already exists
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Hash the password
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
    
    # Create user object for DB
    user_db = UserInDB(
        **user.dict(exclude={"password"}),
        hashed_password=hashed_password.decode('utf-8'),
        created_at=datetime.utcnow()
    )
    
    # Insert user into database
    result = await users_collection.insert_one(user_db.dict(by_alias=True))
    
    # Create access token
    user_id = str(result.inserted_id)
    access_token = create_access_token(
        data={"sub": user.email, "id": user_id}
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user_id": user_id}


@router.post("/login", response_model=Token)
async def login(email: str, password: str):
    # Find user by email
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not bcrypt.checkpw(password.encode('utf-8'), user["hashed_password"].encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    user_id = str(user["_id"])
    access_token = create_access_token(
        data={"sub": email, "id": user_id}
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user_id": user_id}