"""
Session Summarizer Test Runner

Run this script individually to test the session summarizer with specific user and session IDs.
"""

import os
import json
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from crewai import Agent, Task, Crew, Process
from langchain_community.chat_models import ChatLiteLLM

# Import your existing database functions
from backend.database import db, get_user_chat_sessions
import streamlit as st

# Configuration
TEST_USER_ID = "6809c002a03a7a1e240ab91e"
TEST_SESSION_ID = "6809c002a03a7a1e240ab91e"

# Get API key
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    # Fallback for running outside Streamlit
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables or Streamlit secrets")
        exit(1)

# Initialize summarizer collection if it doesn't exist
if "session_summaries" not in db.list_collection_names():
    db.create_collection("session_summaries")
    
# Create TTL index for session_summaries collection (expire after 90 days)
try:
    db.session_summaries.create_index("created_at", expireAfterSeconds=7776000)
except Exception as e:
    print(f"Index may already exist: {e}")

def create_summarizer_agent(api_key):
    """Create an agent specialized in summarizing chat sessions."""
    llm = ChatLiteLLM(
        model="gemini/gemini-2.0-flash-lite",
        api_key=api_key,
        temperature=0.2
    )
    
    return Agent(
        role="Session Summarization Specialist",
        goal="Create concise, accurate summaries of career guidance chat sessions",
        backstory="""
        You are an expert in distilling lengthy conversations into meaningful, actionable summaries.
        Your summaries capture key topics, questions, insights, and follow-up points that will be 
        valuable for future interactions. You're particularly skilled at identifying career guidance themes,
        extracting user goals, and noting areas where additional follow-up would be beneficial.
        """,
        verbose=True,
        llm=llm
    )

def summarize_session_task(messages, user_profile=None, session_id=None, is_incremental=False):
    """Create a task for summarizing a session or portion of a session."""
    
    # Construct conversation text from messages
    conversation = ""
    for msg in messages:
        role = msg.get('role', '').upper()
        content = msg.get('content', '')
        conversation += f"{role}: {content}\n\n"
    
    profile_context = ""
    if user_profile:
        profile_context = f"User profile context: {user_profile}\n\n"
    
    summary_type = "incremental" if is_incremental else "complete"
    
    return Task(
        description=f"""
        {profile_context}
        Review this {summary_type} conversation from a career guidance session:
        
        {conversation}
        
        Create a structured summary with these components:
        
        1. Main topics discussed (list 2-5 key topics)
        2. Key user questions or needs (extract the most important user queries)
        3. Career interests revealed (what career paths or skills is the user interested in?)
        4. Action items discussed (what actions or resources were suggested?)
        5. Follow-up points (what should be followed up on in future sessions?)
        
        Format your response as JSON with these fields:
        {{
            "main_topics": ["topic1", "topic2", ...],
            "key_questions": ["question1", "question2", ...],
            "career_interests": ["interest1", "interest2", ...],
            "action_items": ["action1", "action2", ...],
            "follow_ups": ["follow_up1", "follow_up2", ...],
            "summary_text": "A 2-3 sentence narrative summary of this conversation"
        }}
        
        Keep your summary concise, action-oriented, and focused on information that will be useful for 
        providing context in future sessions.
        """,
        agent=create_summarizer_agent(api_key),
        expected_output="A structured JSON summary of the session conversation."
    )

def save_session_summary(user_id, session_id, summary_data, is_incremental=False):
    """Save a session summary to MongoDB"""
    summary_doc = {
        "user_id": user_id,
        "session_id": session_id,
        "summary_data": summary_data,
        "is_incremental": is_incremental,
        "created_at": datetime.now(timezone.utc)
    }
    
    result = db.session_summaries.insert_one(summary_doc)
    return str(result.inserted_id)

def get_session_messages(session_id):
    """Retrieve messages for a specific session"""
    try:
        # Convert string ID to ObjectId if needed
        if isinstance(session_id, str):
            session_id = ObjectId(session_id)
        
        session = db["chat_sessions"].find_one({"_id": session_id})
        
        if session:
            messages = session.get("messages", [])
            print(f"Found {len(messages)} messages in session")
            return messages
        else:
            print(f"No session found with ID: {session_id}")
            return []
            
    except Exception as e:
        print(f"Error retrieving session messages: {e}")
        return []

def get_user_profile(user_id):
    """Retrieve user profile information"""
    try:
        # Convert string ID to ObjectId if needed
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        
        user = db["users"].find_one({"_id": user_id})
        
        if user:
            # Extract relevant profile information
            profile_info = {
                "name": user.get("name", ""),
                "email": user.get("email", ""),
                "career_stage": user.get("career_stage", ""),
                "interests": user.get("interests", []),
                "goals": user.get("goals", [])
            }
            return profile_info
        else:
            print(f"No user found with ID: {user_id}")
            return None
            
    except Exception as e:
        print(f"Error retrieving user profile: {e}")
        return None

def run_summarizer_test():
    """Main function to test the session summarizer"""
    print("=" * 60)
    print("SESSION SUMMARIZER TEST")
    print("=" * 60)
    print(f"User ID: {TEST_USER_ID}")
    print(f"Session ID: {TEST_SESSION_ID}")
    print()
    
    # Get session messages
    print("1. Retrieving session messages...")
    messages = get_session_messages(TEST_SESSION_ID)
    
    if not messages:
        print("No messages found. Cannot proceed with summarization.")
        return
    
    print(f"   Found {len(messages)} messages")
    
    # Get user profile
    print("2. Retrieving user profile...")
    user_profile = get_user_profile(TEST_USER_ID)
    
    if user_profile:
        print(f"   User profile loaded: {user_profile.get('name', 'No name')}")
    else:
        print("   No user profile found")
    
    # Show sample messages
    print("3. Sample messages:")
    for i, msg in enumerate(messages[:3]):  # Show first 3 messages
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')[:100] + "..." if len(msg.get('content', '')) > 100 else msg.get('content', '')
        print(f"   Message {i+1} ({role}): {content}")
    
    if len(messages) > 3:
        print(f"   ... and {len(messages) - 3} more messages")
    
    print()
    
    # Create and run summarization
    print("4. Creating summarization task...")
    try:
        summary_agent = create_summarizer_agent(api_key)
        summary_task = summarize_session_task(
            messages, 
            user_profile, 
            TEST_SESSION_ID, 
            is_incremental=False
        )
        
        print("5. Running summarization crew...")
        summary_crew = Crew(
            agents=[summary_agent],
            tasks=[summary_task],
            verbose=True,
            process=Process.sequential
        )
        
        result = summary_crew.kickoff()
        print("6. Processing results...")
        
        # Extract JSON from result
        try:
            # Try to parse as JSON directly
            if isinstance(result, dict):
                summary_data = result
            else:
                # Fall back to string parsing
                import re
                
                result_str = str(result)
                # Look for JSON in markdown code blocks
                json_match = re.search(r'```(?:json)?\n(.*?)\n```', result_str, re.DOTALL)
                if json_match:
                    summary_data = json.loads(json_match.group(1))
                else:
                    # Try to parse the whole string
                    try:
                        summary_data = json.loads(result_str)
                    except:
                        # Last resort: create a simple summary dict
                        summary_data = {
                            "main_topics": ["Session summary"],
                            "summary_text": result_str[:500],
                            "raw_result": result_str
                        }
        except Exception as parse_error:
            print(f"Error parsing summary result: {parse_error}")
            summary_data = {
                "main_topics": ["Error parsing summary"],
                "summary_text": "Summary generation completed but parsing failed",
                "raw_result": str(result)
            }
        
        # Display summary
        print("7. Generated Summary:")
        print("-" * 40)
        print(json.dumps(summary_data, indent=2, default=str))
        print("-" * 40)
        
        # Save to database
        print("8. Saving summary to database...")
        summary_id = save_session_summary(
            TEST_USER_ID, 
            TEST_SESSION_ID, 
            summary_data, 
            is_incremental=False
        )
        
        print(f"   Summary saved with ID: {summary_id}")
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during summarization: {e}")
        import traceback
        traceback.print_exc()

def show_existing_summaries():
    """Show existing summaries for the test user/session"""
    print("\n" + "=" * 60)
    print("EXISTING SUMMARIES")
    print("=" * 60)
    
    existing_summaries = list(db.session_summaries.find({
        "user_id": TEST_USER_ID,
        "session_id": TEST_SESSION_ID
    }).sort("created_at", -1))
    
    if existing_summaries:
        print(f"Found {len(existing_summaries)} existing summaries:")
        for i, summary in enumerate(existing_summaries):
            print(f"\nSummary {i+1}:")
            print(f"  Created: {summary['created_at']}")
            print(f"  Incremental: {summary['is_incremental']}")
            print(f"  Data: {json.dumps(summary['summary_data'], indent=4, default=str)}")
    else:
        print("No existing summaries found for this user/session.")

if __name__ == "__main__":
    try:
        # Show existing summaries first
        show_existing_summaries()
        
        # Ask user if they want to proceed
        print("\n" + "=" * 60)
        response = input("Do you want to run the summarizer test? (y/n): ").lower().strip()
        
        if response in ['y', 'yes']:
            run_summarizer_test()
        else:
            print("Test cancelled.")
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()