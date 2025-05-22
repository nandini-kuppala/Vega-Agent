"""
Pattern Analyzer Agent

This agent analyzes patterns in user queries across sessions to identify:
1. Topic progression patterns (basics → roadmaps → timelines → interview prep)
2. Learning style patterns (depth vs. breadth, structured vs. exploratory)
3. Temporal patterns (session timing, frequency, duration)
4. Completion patterns (follow-through on recommended paths)

Patterns are stored in MongoDB for personalized responses in future sessions.
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

# Initialize pattern storage collection if it doesn't exist
if "user_patterns" not in db.list_collection_names():
    db.create_collection("user_patterns")


def create_pattern_analyzer_agent(api_key):
    """Create an agent specialized in identifying patterns in user behavior across sessions."""
    llm = ChatLiteLLM(
        model="gemini/gemini-2.0-flash-lite",
        api_key=api_key,
        temperature=0.2
    )
    
    return Agent(
        role="User Behavior Pattern Analyst",
        goal="Identify meaningful patterns in how users interact with the career guidance chatbot",
        backstory="""
        You are an expert at recognizing behavioral patterns in how people seek career guidance.
        You can identify learning styles, topic progression patterns, engagement habits, and
        completion tendencies from chat histories. Your analysis helps predict what content
        users need next and how they prefer to consume information, making interactions
        more efficient and personalized.
        """,
        verbose=True,
        llm=llm
    )

def extract_user_queries(session_messages):
    """Extract just the user queries from a session for pattern analysis"""
    user_queries = []
    for msg in session_messages:
        if msg.get('role', '').lower() == 'user':
            user_queries.append(msg.get('content', ''))
    return user_queries

def analyze_single_session_pattern_task(user_queries, session_id):
    """
    Create a task for analyzing patterns within a single session
    
    Args:
        user_queries: List of user messages in the session
        session_id: The session ID
    """
    
    queries_text = "\n".join([f"- {query}" for query in user_queries])
    
    return Task(
        description=f"""
        Analyze these user queries from a single career guidance session:
        
        {queries_text}
        
        Identify patterns in the user's approach to career guidance, focusing on:
        
        1. Topic progression: How does the user move through career topics? (e.g., basics → details → application)
        2. Learning style: Does the user prefer depth or breadth? Structured or exploratory learning?
        3. Question style: Are questions specific or general? Practical or theoretical?
        4. Engagement level: How engaged and focused are they on specific topics?
        
        Format your response as JSON with these fields:
        {{
            "topic_progression": "brief description of how user moves between topics",
            "learning_style": "depth_focused|breadth_focused|mixed",
            "learning_approach": "structured|exploratory|mixed",
            "question_specificity": "specific|general|mixed",
            "engagement_level": "high|medium|low",
            "focus_topics": ["topic1", "topic2"],
            "pattern_summary": "2-3 sentence summary of the user's interaction pattern"
        }}
        
        Keep your analysis concise and actionable for personalizing future interactions.
        """,
        agent=create_pattern_analyzer_agent(api_key),
        expected_output="A structured JSON analysis of patterns in the session."
    )

def analyze_cross_session_patterns_task(session_patterns, user_id):
    """
    Create a task for analyzing patterns across multiple sessions
    
    Args:
        session_patterns: List of individual session pattern analyses
        user_id: The user ID
    """
    
    patterns_text = "\n\n".join([
        f"Session {i+1}:\n" + str(pattern)
        for i, pattern in enumerate(session_patterns)
    ])
    
    return Task(
        description=f"""
        Analyze patterns across these multiple career guidance sessions for the same user:
        
        {patterns_text}
        
        Identify consistent patterns and changes in the user's career guidance interactions, focusing on:
        
        1. Consistent topics of interest across sessions
        2. Evolution in learning style or topic depth over time
        3. Patterns in how the user follows career guidance threads across sessions
        4. Changes in specificity or focus of queries over time
        
        Format your response as JSON with these fields:
        {{
            "consistent_interests": ["interest1", "interest2", ...],
            "learning_style_pattern": "description of overall learning style with any evolution noted",
            "preferred_learning_depth": "deep_diver|broad_explorer|evolving|mixed",
            "follow_through_pattern": "description of how user follows up on topics across sessions",
            "query_evolution": "description of how queries have changed over time",
            "recommended_approach": "suggested approach for future interactions based on patterns",
            "pattern_summary": "3-4 sentence summary of the user's cross-session interaction patterns"
        }}
        
        Make your analysis actionable for improving the efficiency and personalization of future interactions.
        Focus especially on patterns that could help predict what guidance will be most useful next.
        """,
        agent=create_pattern_analyzer_agent(api_key),
        expected_output="A structured JSON analysis of cross-session patterns."
    )

def save_session_pattern(user_id, session_id, pattern_data):
    """
    Save a session pattern analysis to MongoDB
    
    Args:
        user_id: User ID
        session_id: Session ID
        pattern_data: The pattern analysis dictionary
    """
    pattern_doc = {
        "user_id": user_id,
        "session_id": session_id,
        "pattern_data": pattern_data,
        "created_at": datetime.now(timezone.utc)
    }
    
    result = db.session_patterns.insert_one(pattern_doc)
    return str(result.inserted_id)


def save_cross_session_pattern(user_id, pattern_data):
    """
    Save or update a cross-session pattern analysis to MongoDB
    
    Args:
        user_id: User ID
        pattern_data: The cross-session pattern analysis dictionary
    """
    # Check if we already have a pattern document for this user
    existing_pattern = db.user_patterns.find_one({"user_id": user_id})
    
    if existing_pattern:
        # Update existing document
        db.user_patterns.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "pattern_data": pattern_data,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return str(existing_pattern["_id"])
    else:
        # Create new document
        pattern_doc = {
            "user_id": user_id,
            "pattern_data": pattern_data,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        result = db.user_patterns.insert_one(pattern_doc)
        return str(result.inserted_id)

def analyze_session_pattern(user_id, session_id, messages):
    """
    Analyze patterns within a single session
    
    Args:
        user_id: User ID
        session_id: Session ID
        messages: List of session messages
    
    Returns:
        pattern_id if analysis was created, None otherwise
    """
    # Only analyze sessions with at least 3 user queries
    user_queries = extract_user_queries(messages)
    if len(user_queries) < 3:
        return None
    
    # Create and execute pattern analysis task
    pattern_agent = create_pattern_analyzer_agent(api_key)
    pattern_task = analyze_single_session_pattern_task(user_queries, session_id)
    
    pattern_crew = Crew(
        agents=[pattern_agent],
        tasks=[pattern_task],
        verbose=False,
        process=Process.sequential
    )
    
    result = pattern_crew.kickoff()
    
    # Extract JSON from result
    try:
        # Try to parse as JSON directly
        pattern_data = dict(result)
    except:
        # Fall back to string parsing if result is not a dict
        import json
        import re
        
        result_str = str(result)
        # Look for JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\n(.*?)\n```', result_str, re.DOTALL)
        if json_match:
            pattern_data = json.loads(json_match.group(1))
        else:
            # Try to parse the whole string
            try:
                pattern_data = json.loads(result_str)
            except:
                # Last resort: create a simple pattern dict
                pattern_data = {
                    "pattern_summary": result_str[:500],  # Truncate if needed
                    "raw_result": result_str
                }
    
    # Save the pattern analysis to MongoDB
    pattern_id = save_session_pattern(user_id, session_id, pattern_data)
    
    # Check if we should update cross-session analysis
    should_update_cross_session = should_analyze_cross_session_patterns(user_id)
    if should_update_cross_session:
        analyze_cross_session_patterns(user_id)
    
    return pattern_id

def should_analyze_cross_session_patterns(user_id):
    """
    Determine if cross-session pattern analysis should be performed
    
    Args:
        user_id: User ID
    
    Returns:
        bool: Whether cross-session analysis should be performed
    """
    # Get the last cross-session analysis
    last_analysis = db.user_patterns.find_one(
        {"user_id": user_id},
        sort=[("updated_at", -1)]
    )
    
    # If no previous analysis, do it if we have at least 2 sessions
    if not last_analysis:
        session_count = db.session_patterns.count_documents({"user_id": user_id})
        return session_count >= 2
    
    # If previous analysis exists, check if it's older than 24 hours 
    # and we have new session patterns since then
    last_update = last_analysis["updated_at"]
    time_since_update = datetime.now(timezone.utc) - last_update
    
    if time_since_update > timedelta(hours=24):
        # Check if we have new session patterns since last update
        new_patterns = db.session_patterns.count_documents({
            "user_id": user_id,
            "created_at": {"$gt": last_update}
        })
        return new_patterns > 0
    
    return False

def analyze_cross_session_patterns(user_id, max_sessions=5):
    """
    Analyze patterns across multiple sessions for a user
    
    Args:
        user_id: User ID
        max_sessions: Maximum number of recent sessions to analyze
    
    Returns:
        pattern_id if analysis was created, None otherwise
    """
    # Get recent session patterns
    session_patterns = list(db.session_patterns.find(
        {"user_id": user_id},
        {"pattern_data": 1}
    ).sort("created_at", -1).limit(max_sessions))
    
    if len(session_patterns) < 2:
        return None
    
    # Extract pattern data
    pattern_data_list = [sp["pattern_data"] for sp in session_patterns]
    
    # Create and execute cross-session analysis task
    pattern_agent = create_pattern_analyzer_agent(api_key)
    cross_session_task = analyze_cross_session_patterns_task(pattern_data_list, user_id)
    
    cross_session_crew = Crew(
        agents=[pattern_agent],
        tasks=[cross_session_task],
        verbose=False,
        process=Process.sequential
    )
    
    result = cross_session_crew.kickoff()
    
    # Extract JSON from result
    try:
        # Try to parse as JSON directly
        pattern_data = dict(result)
    except:
        # Fall back to string parsing if result is not a dict
        import json
        import re
        
        result_str = str(result)
        # Look for JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\n(.*?)\n```', result_str, re.DOTALL)
        if json_match:
            pattern_data = json.loads(json_match.group(1))
        else:
            # Try to parse the whole string
            try:
                pattern_data = json.loads(result_str)
            except:
                # Last resort: create a simple pattern dict
                pattern_data = {
                    "pattern_summary": result_str[:500],  # Truncate if needed
                    "raw_result": result_str
                }
    
    # Save the cross-session pattern analysis to MongoDB
    pattern_id = save_cross_session_pattern(user_id, pattern_data)
    
    return pattern_id

def get_user_pattern_summary(user_id):
    """
    Get the most recent cross-session pattern analysis for a user
    
    Args:
        user_id: User ID
    
    Returns:
        Pattern data dictionary or None if not found
    """
    pattern_doc = db.user_patterns.find_one(
        {"user_id": user_id},
        sort=[("updated_at", -1)]
    )
    
    if pattern_doc:
        return pattern_doc["pattern_data"]
    
    # If no cross-session pattern exists, try to get the most recent single session pattern
    single_pattern = db.session_patterns.find_one(
        {"user_id": user_id},
        sort=[("created_at", -1)]
    )
    
    if single_pattern:
        return {
            "pattern_summary": single_pattern["pattern_data"].get("pattern_summary", "First session analysis"),
            "is_single_session": True
        }
    
    return None