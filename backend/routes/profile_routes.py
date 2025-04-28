from fastapi import APIRouter, HTTPException, status
from typing import List
from bson import ObjectId

from models.user_model import ProfileCreate, ProfileInDB, ProfileResponse
from database import profiles_collection, users_collection

router = APIRouter()


@router.post("/create", response_model=ProfileResponse)
async def create_profile(profile: ProfileCreate):
    # Verify user exists
    user_id = profile.user_id
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if profile for this user already exists
    existing_profile = await profiles_collection.find_one({"user_id": user_id})
    if existing_profile:
        # Update existing profile
        await profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": profile.dict()}
        )
        updated_profile = await profiles_collection.find_one({"user_id": user_id})
        return {**updated_profile, "id": str(updated_profile["_id"])}
    
    # Create new profile
    profile_db = ProfileInDB(**profile.dict())
    result = await profiles_collection.insert_one(profile_db.dict(by_alias=True))
    
    # Return the created profile
    created_profile = await profiles_collection.find_one({"_id": result.inserted_id})
    return {**created_profile, "id": str(created_profile["_id"])}


@router.get("/{user_id}", response_model=ProfileResponse)
async def get_profile(user_id: str):
    profile = await profiles_collection.find_one({"user_id": user_id})
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return {**profile, "id": str(profile["_id"])}