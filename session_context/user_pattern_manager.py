"""
User Pattern Manager

This agent is responsible for comparing patterns across sessions to identify:
1. Consistent learning preferences over time
2. Topic interest evolution (tracking how interests change)
3. Engagement pattern shifts (session frequency, depth, follow-through)
4. Personalization opportunities based on observed patterns

This information is used to personalize responses and suggest optimal content delivery methods.
"""

import os
from datetime import datetime, timezone, timedelta
import json

from bson import ObjectId

from crewai import Agent, Task, Crew, Process
from langchain_community.chat_models import ChatLiteLLM

# Use your existing database functions
from backend.database import db
import streamlit as st

api_key = st.secrets["GEMINI_API_KEY"]
# Initialize user preference collection if it doesn't exist
if "user_preferences" not in db.list_collection_names():
    db.create_collection("user_preferences")

def create_pattern_manager_agent(api_key):
    """Create an agent specialized in managing user interaction patterns."""
    llm = ChatLiteLLM(
        model="gemini/gemini-2.0-flash-lite",
        api_key=api_key,
        temperature=0.2
    )
    
    return Agent(
        role="User Pattern Manager",
        goal="Identify and track evolving user interaction patterns to personalize career guidance",
        backstory="""
        You are an expert at recognizing how people's learning preferences and career interests 
        evolve over time. You excel at spotting subtle shifts in engagement patterns and identifying 
        opportunities for personalization based on observed behavior. Your insights help ensure 
        that career guidance adapts to each user's unique and changing needs.
        """,
        verbose=True,
        llm=llm
    )

def get_session_patterns(user_id, limit=5):
    """
    Get patterns from recent sessions for a user
    
    Args:
        user_id: User ID
        limit: Maximum number of pattern documents to retrieve
    
    Returns:
        List of session pattern documents
    """
    patterns = list(db.session_patterns.find(
        {"user_id": user_id},
        {"session_id": 1, "pattern_data": 1, "created_at": 1}
    ).sort("created_at", -1).limit(limit))
    
    return patterns

def get_cross_session_pattern(user_id):
    """
    Get the most recent cross-session pattern analysis for a user
    
    Args:
        user_id: User ID
    
    Returns:
        Cross-session pattern document or None if not found
    """
    return db.user_patterns.find_one(
        {"user_id": user_id},
        {"pattern_data": 1, "updated_at": 1}
    )

def compare_patterns_task(session_patterns, cross_session_pattern=None):
    """
    Create a task for comparing patterns and identifying evolution
    
    Args:
        session_patterns: List of session pattern documents
        cross_session_pattern: Optional cross-session pattern document
    """
    # Format session patterns for the task
    formatted_patterns = []
    for i, pattern in enumerate(session_patterns):
        timestamp = pattern["created_at"].strftime("%Y-%m-%d %H:%M")
        formatted_patterns.append(
            f"Session {i+1} ({timestamp}):\n{json.dumps(pattern['pattern_data'], indent=2)}"
        )
    
    patterns_text = "\n\n".join(formatted_patterns)
    
    # Add cross-session pattern if available
    cross_session_text = ""
    if cross_session_pattern:
        timestamp = cross_session_pattern["updated_at"].strftime("%Y-%m-%d %H:%M")
        cross_session_text = f"""
        Previous cross-session analysis ({timestamp}):
        {json.dumps(cross_session_pattern['pattern_data'], indent=2)}
        """
    
    return Task(
        description=f"""
        Compare these user interaction patterns from career guidance sessions:
        
        {patterns_text}
        
        {cross_session_text}
        
        Your task is to identify:
        
        1. How the user's learning preferences have evolved over time
        2. Changes in topic interests or career focus
        3. Shifts in engagement patterns or question styles
        4. Personalization opportunities based on consistent or emerging patterns
        
        Format your response as JSON with these fields:
        {{
            "learning_preference_evolution": "description of how learning preferences have changed",
            "topic_interest_evolution": "description of how interests have shifted",
            "engagement_pattern_shifts": "description of engagement pattern changes",
            "consistent_preferences": ["preference1", "preference2", ...],
            "emerging_preferences": ["preference1", "preference2", ...],
            "personalization_recommendations": [
                {{
                    "aspect": "content_depth|interaction_style|topic_suggestions|content_format",
                    "recommendation": "specific recommendation",
                    "rationale": "why this would improve experience"
                }},
                ...
            ],
            "evolution_summary": "3-4 sentence summary of key pattern evolution insights"
        }}
        
        Focus on actionable insights that can improve the user's experience in future sessions.
        """,
        agent=create_pattern_manager_agent(api_key),
        expected_output="A structured JSON analysis of pattern evolution and personalization recommendations."
    )

def save_user_preferences(user_id, preferences_data):
    """
    Save or update user preferences in MongoDB
    
    Args:
        user_id: User ID
        preferences_data: The preferences and recommendations dictionary
    """
    # Check if we already have a preferences document for this user
    existing_prefs = db.user_preferences.find_one({"user_id": user_id})
    
    if existing_prefs:
        # Update existing document
        db.user_preferences.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "preferences_data": preferences_data,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return str(existing_prefs["_id"])
    else:
        # Create new document
        prefs_doc = {
            "user_id": user_id,
            "preferences_data": preferences_data,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        result = db.user_preferences.insert_one(prefs_doc)
        return str(result.inserted_id)

def should_update_preferences(user_id):
    """
    Determine if user preferences should be updated
    
    Args:
        user_id: User ID
    
    Returns:
        bool: Whether preferences should be updated
    """
    # Get the last preferences update
    last_prefs = db.user_preferences.find_one(
        {"user_id": user_id},
        sort=[("updated_at", -1)]
    )
    
    # If no previous preferences, update if we have at least 2 session patterns
    if not last_prefs:
        session_count = db.session_patterns.count_documents({"user_id": user_id})
        return session_count >= 2
    
    # If previous preferences exist, check if they're older than 3 days 
    # and we have new session patterns since then
    last_update = last_prefs["updated_at"]
    time_since_update = datetime.now(timezone.utc) - last_update
    
    if time_since_update > timedelta(days=3):
        # Check if we have new session patterns since last update
        new_patterns = db.session_patterns.count_documents({
            "user_id": user_id,
            "created_at": {"$gt": last_update}
        })
        return new_patterns > 0
    
    return False

def analyze_pattern_evolution(user_id, max_sessions=5):
    """
    Analyze evolution of patterns across sessions and update user preferences
    
    Args:
        user_id: User ID
        max_sessions: Maximum number of recent session patterns to analyze
    
    Returns:
        preferences_id if analysis was created/updated, None otherwise
    """
    # Check if we should update
    if not should_update_preferences(user_id):
        return None
    
    # Get recent session patterns
    session_patterns = get_session_patterns(user_id, limit=max_sessions)
    
    if len(session_patterns) < 2:
        return None
    
    # Get existing cross-session pattern if available
    cross_session_pattern = get_cross_session_pattern(user_id)
    
    # Create and execute pattern evolution analysis task
    pattern_agent = create_pattern_manager_agent(api_key)
    pattern_task = compare_patterns_task(session_patterns, cross_session_pattern)
    
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
        preferences_data = dict(result)
    except:
        # Fall back to string parsing if result is not a dict
        import json
        import re
        
        result_str = str(result)
        # Look for JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\n(.*?)\n```', result_str, re.DOTALL)
        if json_match:
            preferences_data = json.loads(json_match.group(1))
        else:
            # Try to parse the whole string
            try:
                preferences_data = json.loads(result_str)
            except:
                # Last resort: create a simple preferences dict
                preferences_data = {
                    "evolution_summary": result_str[:500],  # Truncate if needed
                    "raw_result": result_str
                }
    
    # Save the preferences to MongoDB
    preferences_id = save_user_preferences(user_id, preferences_data)
    
    return preferences_id

def get_personalization_recommendations(user_id):
    """
    Get personalization recommendations for a user
    
    Args:
        user_id: User ID
    
    Returns:
        List of personalization recommendations or None if not available
    """
    preferences = db.user_preferences.find_one(
        {"user_id": user_id},
        {"preferences_data": 1}
    )
    
    if preferences and "preferences_data" in preferences:
        return preferences["preferences_data"].get("personalization_recommendations", None)
    
    return None

def get_content_delivery_preferences(user_id):
    """
    Get content delivery preferences for a user
    
    Args:
        user_id: User ID
    
    Returns:
        Dictionary with content delivery preferences or default values
    """
    preferences = db.user_preferences.find_one(
        {"user_id": user_id},
        {"preferences_data": 1}
    )
    
    # Default preferences
    delivery_prefs = {
        "content_depth": "balanced",  # balanced, detailed, concise
        "interaction_style": "conversational",  # conversational, structured, exploratory
        "content_format": "mixed"  # text-heavy, examples-focused, mixed
    }
    
    if preferences and "preferences_data" in preferences:
        prefs_data = preferences["preferences_data"]
        
        # Extract consistent preferences
        consistent = prefs_data.get("consistent_preferences", [])
        for pref in consistent:
            pref_lower = pref.lower()
            
            # Update content depth preference
            if "deep" in pref_lower or "detail" in pref_lower:
                delivery_prefs["content_depth"] = "detailed"
            elif "concise" in pref_lower or "brief" in pref_lower:
                delivery_prefs["content_depth"] = "concise"
                
            # Update interaction style preference
            if "structured" in pref_lower or "guided" in pref_lower:
                delivery_prefs["interaction_style"] = "structured"
            elif "explore" in pref_lower or "discover" in pref_lower:
                delivery_prefs["interaction_style"] = "exploratory"
                
            # Update content format preference
            if "example" in pref_lower or "practical" in pref_lower:
                delivery_prefs["content_format"] = "examples-focused"
            elif "theoretical" in pref_lower or "concepts" in pref_lower:
                delivery_prefs["content_format"] = "text-heavy"
        
        # Check explicit recommendations
        recommendations = prefs_data.get("personalization_recommendations", [])
        for rec in recommendations:
            aspect = rec.get("aspect", "")
            if aspect == "content_depth" and "recommendation" in rec:
                rec_text = rec["recommendation"].lower()
                if "detailed" in rec_text or "depth" in rec_text:
                    delivery_prefs["content_depth"] = "detailed"
                elif "concise" in rec_text or "brief" in rec_text:
                    delivery_prefs["content_depth"] = "concise"
            
            elif aspect == "interaction_style" and "recommendation" in rec:
                rec_text = rec["recommendation"].lower()
                if "structured" in rec_text:
                    delivery_prefs["interaction_style"] = "structured"
                elif "exploratory" in rec_text:
                    delivery_prefs["interaction_style"] = "exploratory"
                elif "conversational" in rec_text:
                    delivery_prefs["interaction_style"] = "conversational"
            
            elif aspect == "content_format" and "recommendation" in rec:
                rec_text = rec["recommendation"].lower()
                if "example" in rec_text:
                    delivery_prefs["content_format"] = "examples-focused"
                elif "text" in rec_text or "concept" in rec_text:
                    delivery_prefs["content_format"] = "text-heavy"
    
    return delivery_prefs

def apply_personalization_to_prompt(base_prompt, user_id):
    """
    Apply personalization based on user preferences to a base prompt
    
    Args:
        base_prompt: Base prompt text
        user_id: User ID
    
    Returns:
        Personalized prompt
    """
    delivery_prefs = get_content_delivery_preferences(user_id)
    
    # Apply content depth preference
    if delivery_prefs["content_depth"] == "detailed":
        base_prompt += "\nPlease provide detailed explanations with supporting information."
    elif delivery_prefs["content_depth"] == "concise":
        base_prompt += "\nPlease provide concise, to-the-point responses."
    
    # Apply interaction style preference
    if delivery_prefs["interaction_style"] == "structured":
        base_prompt += "\nOrganize your response in a clear, structured format with sections."
    elif delivery_prefs["interaction_style"] == "exploratory":
        base_prompt += "\nInclude alternative perspectives or approaches where relevant."
    
    # Apply content format preference
    if delivery_prefs["content_format"] == "examples-focused":
        base_prompt += "\nInclude concrete examples to illustrate your points."
    elif delivery_prefs["content_format"] == "text-heavy":
        base_prompt += "\nFocus on conceptual explanations and theoretical foundations."
    
    return base_prompt

def recommend_topic_based_on_patterns(user_id):
    """
    Recommend a topic based on user interaction patterns
    
    Args:
        user_id: User ID
    
    Returns:
        Dictionary with topic recommendation and rationale
    """
    # Get cross-session pattern
    pattern = get_cross_session_pattern(user_id)
    
    # Default recommendation
    recommendation = {
        "topic": "career assessment",
        "rationale": "Many users benefit from starting with a self-assessment to identify strengths and interests.",
        "confidence": "low"
    }
    
    if pattern and "pattern_data" in pattern:
        pattern_data = pattern["pattern_data"]
        
        # Check for consistent interests
        interests = pattern_data.get("consistent_interests", [])
        if interests:
            # Return the most consistent interest
            recommendation = {
                "topic": interests[0],
                "rationale": f"This topic has been a consistent interest across your sessions.",
                "confidence": "high"
            }
        
        # Check for emerging preferences
        emerging = pattern_data.get("emerging_preferences", [])
        if emerging and not interests:
            recommendation = {
                "topic": emerging[0],
                "rationale": f"Based on your recent interactions, this appears to be an emerging interest.",
                "confidence": "medium"
            }
    
    return recommendation

def get_session_engagement_metrics(user_id, days=30):
    """
    Get engagement metrics for a user across sessions
    
    Args:
        user_id: User ID
        days: Number of days to look back
    
    Returns:
        Dictionary with engagement metrics
    """
    since_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Count sessions in the time period
    session_count = db.session_patterns.count_documents({
        "user_id": user_id,
        "created_at": {"$gt": since_date}
    })
    
    # Get pattern evolution if available
    pattern_evolution = None
    preferences = db.user_preferences.find_one({"user_id": user_id})
    if preferences and "preferences_data" in preferences:
        pattern_evolution = preferences["preferences_data"].get("engagement_pattern_shifts")
    
    return {
        "session_count": session_count,
        "pattern_evolution": pattern_evolution,
        "last_update": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    }