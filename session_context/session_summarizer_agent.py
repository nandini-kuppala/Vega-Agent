"""
Session Summarizer Agent

This agent is responsible for generating summaries of chat sessions.
It creates summaries in the following scenarios:
1. When a user ends a session
2. After a period of inactivity (30 minutes)
3. After every 15 messages in a long session (incremental summaries)

Summaries are stored in MongoDB for context retrieval in future sessions.
"""

import os
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from crewai import Agent, Task, Crew, Process
from langchain_community.chat_models import ChatLiteLLM

# Use your existing database functions
from backend.database import db
import streamlit as st

api_key = st.secrets["GEMINI_API_KEY"]

# Initialize summarizer collection if it doesn't exist
if "session_summaries" not in db.list_collection_names():
    db.create_collection("session_summaries")
    
# Create TTL index for session_summaries collection (expire after 90 days)
db.session_summaries.create_index("created_at", expireAfterSeconds=7776000)

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
    """
    Create a task for summarizing a session or portion of a session.
    
    Args:
        messages: List of message objects with 'role' and 'content'
        user_profile: Optional user profile information for context
        session_id: The session ID
        is_incremental: Whether this is an incremental summary within an ongoing session
    """
    
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
    """
    Save a session summary to MongoDB
    
    Args:
        user_id: User ID
        session_id: Session ID
        summary_data: The summary dictionary
        is_incremental: Whether this is an incremental summary
    """
    summary_doc = {
        "user_id": user_id,
        "session_id": session_id,
        "summary_data": summary_data,
        "is_incremental": is_incremental,
        "created_at": datetime.now(timezone.utc)
    }
    
    result = db.session_summaries.insert_one(summary_doc)
    return str(result.inserted_id)
