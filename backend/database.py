from pymongo import MongoClient
from dotenv import load_dotenv
import os
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import json
# Load environment variables from .env file
load_dotenv()

# Secret key for JWT
SECRET_KEY = "asha_ai_secret_key"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Retrieve the MONGO_URI from the environment variables
MONGO_URI = os.getenv("MONGO_URI")

# Initialize the MongoDB client
client = MongoClient(MONGO_URI)
db = client["asha_bot"]

# Collections
users_collection = db["users"]
profiles_collection = db["profiles"]

# User Authentication Functions
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def signup_user(email, password, name, phone=None, city=None):
    # Check if user with this email already exists
    existing_user = users_collection.find_one({"email": email})
    if existing_user:
        return {"status": "error", "message": "User with this email already exists"}
    
    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Create user object for DB
    user_db = {
        "email": email,
        "name": name,
        "hashed_password": hashed_password,
        "created_at": datetime.now(timezone.utc)
    }
    
    # Add optional fields if provided
    if phone:
        user_db["phone"] = phone
    if city:
        user_db["city"] = city
    
    # Insert user into database
    result = users_collection.insert_one(user_db)
    
    # Create access token
    user_id = str(result.inserted_id)
    access_token = create_access_token(
        data={"sub": email, "id": user_id}
    )
    
    return {
        "status": "success", 
        "access_token": access_token, 
        "token_type": "bearer", 
        "user_id": user_id
    }

def login_user(email, password):
    # Find user by email
    user = users_collection.find_one({"email": email})
    if not user:
        return {"status": "error", "message": "Incorrect email or password"}
    
    # Verify password
    if not bcrypt.checkpw(password.encode('utf-8'), user["hashed_password"].encode('utf-8')):
        return {"status": "error", "message": "Incorrect email or password"}
    
    # Create access token
    user_id = str(user["_id"])
    access_token = create_access_token(
        data={"sub": email, "id": user_id}
    )
    
    return {
        "status": "success", 
        "access_token": access_token, 
        "token_type": "bearer", 
        "user_id": user_id
    }

# Profile Management Functions
def create_profile(profile_data):
    # Verify user exists
    user_id = profile_data["user_id"]
    try:
        user = users_collection.find_one({"_id": ObjectId(user_id)})
    except:
        return {"status": "error", "message": "Invalid user ID format"}
        
    if not user:
        return {"status": "error", "message": "User not found"}
    
    # Check if profile for this user already exists
    existing_profile = profiles_collection.find_one({"user_id": user_id})
    if existing_profile:
        # Update existing profile
        profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": profile_data}
        )
        updated_profile = profiles_collection.find_one({"user_id": user_id})
        return {
            "status": "success", 
            "profile": {**{k: v for k, v in updated_profile.items() if k != "_id"}, "id": str(updated_profile["_id"])}
        }
    
    # Create new profile
    result = profiles_collection.insert_one(profile_data)
    
    # Return the created profile
    created_profile = profiles_collection.find_one({"_id": result.inserted_id})
    return {
        "status": "success", 
        "profile": {**{k: v for k, v in created_profile.items() if k != "_id"}, "id": str(created_profile["_id"])}
    }

def get_profile(user_id):
    try:
        # First check if the user exists
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            return {"status": "error", "message": "User not found"}
            
        profile = profiles_collection.find_one({"user_id": user_id})
        if not profile:
            return {"status": "error", "message": "Profile not found"}
        
        # Convert ObjectId to string representation
        profile_dict = {k: v for k, v in profile.items() if k != "_id"}
        profile_dict["id"] = str(profile["_id"])
        
        return {"status": "success", "profile": profile_dict}
    except Exception as e:
        return {"status": "error", "message": f"Error retrieving profile: {str(e)}"}

def get_user_details(user_id):
    """
    Retrieve user details from the users collection.
    
    Args:
        user_id (str): The ID of the user to retrieve.
        
    Returns:
        dict: A dictionary containing the user's details or an error message.
    """
    try:
        # Convert string ID to ObjectId
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return {"status": "error", "message": "User not found"}
        
        # Create a cleaned user dict without sensitive information
        user_dict = {
            "id": str(user["_id"]),
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "phone": user.get("phone", ""),
            "city": user.get("city", ""),
            "created_at": user.get("created_at", "")
        }
        
        return {"status": "success", "user": user_dict}
    except Exception as e:
        return {"status": "error", "message": f"Error retrieving user details: {str(e)}"}
# Add these functions to your database.py file:
def sanitize_response(response):
    """Convert any non-serializable response objects to string"""
    # Handle CrewOutput objects
    if hasattr(response, '__class__') and response.__class__.__name__ == 'CrewOutput':
        try:
            return response.raw  # Extract the raw text from CrewOutput
        except:
            return str(response)  # Fallback to string representation
    
    # Handle other object types that might not be JSON serializable
    try:
        # Test if the object is JSON serializable
        json.dumps(response)
        return response
    except (TypeError, OverflowError):
        return str(response)
# Chat Storage Functions
def save_chat_history(user_id, messages):
    """
    Save or update chat history for a user in MongoDB
    """
    # Sanitize messages before saving
    sanitized_messages = []
    for msg in messages:
        sanitized_msg = msg.copy()
        if 'content' in sanitized_msg:
            sanitized_msg['content'] = sanitize_response(sanitized_msg['content'])
        sanitized_messages.append(sanitized_msg)
    
    try:
        # Check if chat history already exists for this user
        existing_chat = db["chats"].find_one({"user_id": user_id})
        
        if existing_chat:
            # Update existing chat history
            db["chats"].update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "messages": sanitized_messages,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
        else:
            # Create new chat history
            db["chats"].insert_one({
                "user_id": user_id,
                "messages": sanitized_messages,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            })
        
        return {"status": "success", "message": "Chat history saved"}
    except Exception as e:
        # Log the error but return a status so the chat can continue
        print(f"Error saving chat history: {str(e)}")
        return {"status": "error", "message": str(e)}
    

def get_chat_history(user_id):
    """
    Retrieve chat history for a user from MongoDB
    """
    chat_history = db["chats"].find_one({"user_id": user_id})
    
    if not chat_history:
        return {"status": "success", "messages": []}
    
    return {"status": "success", "messages": chat_history.get("messages", [])}


def create_chat_session(user_id, title="New Chat"):
    """Create a new chat session for a user"""
    try:
        session_data = {
            "user_id": user_id,
            "title": title,
            "messages": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "is_active": True
        }
        
        result = db["chat_sessions"].insert_one(session_data)
        session_id = str(result.inserted_id)
        
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_user_chat_sessions(user_id, limit=20):
    """Get all chat sessions for a user, ordered by most recent"""
    try:
        sessions = list(db["chat_sessions"].find(
            {"user_id": user_id}, 
            {"title": 1, "created_at": 1, "updated_at": 1, "message_count": {"$size": "$messages"}}
        ).sort("updated_at", -1).limit(limit))
        
        # Convert ObjectId to string
        for session in sessions:
            session["_id"] = str(session["_id"])
            
        return {"status": "success", "sessions": sessions}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_chat_session(session_id):
    """Get a specific chat session by ID"""
    try:
        session = db["chat_sessions"].find_one({"_id": ObjectId(session_id)})
        if not session:
            return {"status": "error", "message": "Session not found"}
        
        # Convert ObjectId to string
        session["_id"] = str(session["_id"])
        return {"status": "success", "session": session}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def save_session_messages(session_id, messages):
    """Save messages to a specific chat session"""
    try:
        # Sanitize messages before saving
        sanitized_messages = []
        for msg in messages:
            sanitized_msg = msg.copy()
            if 'content' in sanitized_msg:
                sanitized_msg['content'] = sanitize_response(sanitized_msg['content'])
            sanitized_messages.append(sanitized_msg)
        
        # Generate title from first user message if title is "New Chat"
        session = db["chat_sessions"].find_one({"_id": ObjectId(session_id)})
        title = session.get("title", "New Chat")
        
        if title == "New Chat" and sanitized_messages:
            # Find first user message to generate title
            for msg in sanitized_messages:
                if msg.get("role") == "user":
                    title = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
                    break
        
        db["chat_sessions"].update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "messages": sanitized_messages,
                    "title": title,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        return {"status": "success", "message": "Messages saved"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def delete_chat_session(session_id, user_id):
    """Delete a chat session (verify ownership)"""
    try:
        result = db["chat_sessions"].delete_one({
            "_id": ObjectId(session_id),
            "user_id": user_id
        })
        
        if result.deleted_count == 0:
            return {"status": "error", "message": "Session not found or not authorized"}
        
        return {"status": "success", "message": "Session deleted"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def update_session_title(session_id, user_id, new_title):
    """Update the title of a chat session"""
    try:
        result = db["chat_sessions"].update_one(
            {"_id": ObjectId(session_id), "user_id": user_id},
            {"$set": {"title": new_title, "updated_at": datetime.now(timezone.utc)}}
        )
        
        if result.matched_count == 0:
            return {"status": "error", "message": "Session not found or not authorized"}
        
        return {"status": "success", "message": "Title updated"}
    except Exception as e:
        return {"status": "error", "message": str(e)}