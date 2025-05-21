"""
Session Context Manager

This agent retrieves and consolidates summaries from previous sessions to provide
contextual information for the current session, including follow-up recommendations.

It focuses on:
1. Retrieving the most relevant previous session summaries (2-3)
2. Consolidating them into a concise context
3. Generating follow-up recommendations based on past interactions
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

def create_context_manager_agent(api_key):
    """Create an agent specialized in managing cross-session context."""
    llm = ChatLiteLLM(
        model="gemini/gemini-2.0-flash-lite",
        api_key=api_key,
        temperature=0.2
    )
    
    return Agent(
        role="Session Context Manager",
        goal="Provide concise, relevant context from previous sessions to enhance the current interaction",
        backstory="""
        You are an expert at understanding what past interactions are most relevant to the current 
        conversation. You excel at consolidating information from previous sessions into a concise, 
        actionable format that helps continue conversations seamlessly across multiple interactions.
        You're particularly skilled at identifying unresolved threads and opportunities for meaningful
        follow-ups that demonstrate continuity and personalization.
        """,
        verbose=True,
        llm=llm
    )

def get_recent_session_summaries(user_id, limit=3, exclude_session_id=None):
    """
    Get recent session summaries for a user
    
    Args:
        user_id: User ID
        limit: Maximum number of summaries to retrieve
        exclude_session_id: Optional session ID to exclude (current session)
    
    Returns:
        List of session summary documents
    """
    query = {"user_id": user_id}
    if exclude_session_id:
        query["session_id"] = {"$ne": exclude_session_id}
    
    summaries = list(db.session_summaries.find(
        query,
        {"session_id": 1, "summary_data": 1, "created_at": 1}
    ).sort("created_at", -1).limit(limit))
    
    return summaries

def prepare_consolidated_context_task(summaries, current_query=None):
    """
    Create a task for consolidating context from previous sessions
    
    Args:
        summaries: List of session summary documents
        current_query: Optional current user query for context
    """
    
    summaries_text = "\n\n".join([
        f"Session {i+1} ({summary['created_at'].strftime('%Y-%m-%d %H:%M')}): {summary['summary_data']}"
        for i, summary in enumerate(summaries)
    ])
    
    current_context = ""
    if current_query:
        current_context = f"\nThe user's current query is: \"{current_query}\"\n"
    
    return Task(
        description=f"""
        Review these summaries from the user's previous career guidance sessions:
        
        {summaries_text}
        {current_context}
        
        Your task is to create a concise, cohesive context that highlights:
        
        1. The most important topics and interests from previous sessions
        2. Key questions or needs that are likely still relevant
        3. Action items or recommendations that were previously discussed
        4. Specific follow-up points that should be addressed in this session
        
        Format your response as JSON with these fields:
        {{
            "key_context_points": ["point1", "point2", ...],
            "ongoing_interests": ["interest1", "interest2", ...],
            "previous_recommendations": ["recommendation1", "recommendation2", ...],
            "follow_up_recommendations": ["follow_up1", "follow_up2", ...],
            "context_summary": "A 2-3 sentence summary of relevant previous context"
        }}
        
        Keep your consolidated context very concise (maximum 150 words total), focusing only 
        on the most relevant information for the current interaction.
        """,
        agent=create_context_manager_agent(api_key),
        expected_output="A concise JSON summary of relevant context from previous sessions."
    )

def generate_consolidated_context(user_id, current_session_id=None, current_query=None, limit=3):
    """
    Generate consolidated context from previous sessions
    
    Args:
        user_id: User ID
        current_session_id: Optional current session ID to exclude
        current_query: Optional current user query
        limit: Maximum number of previous sessions to consider
        
    Returns:
        Consolidated context dictionary
    """
    # Get recent session summaries
    summaries = get_recent_session_summaries(
        user_id, 
        limit=limit, 
        exclude_session_id=current_session_id
    )
    
    # If no previous summaries, return empty context
    if not summaries:
        return {
            "key_context_points": [],
            "follow_up_recommendations": [],
            "context_summary": "No previous session context available."
        }
    
    # Create and execute consolidation task
    context_agent = create_context_manager_agent(api_key)
    context_task = prepare_consolidated_context_task(summaries, current_query)
    
    context_crew = Crew(
        agents=[context_agent],
        tasks=[context_task],
        verbose=False,
        process=Process.sequential
    )
    
    result = context_crew.kickoff()
    
    # Extract JSON from result
    try:
        # Try to parse as JSON directly
        context_data = dict(result)
    except:
        # Fall back to string parsing if result is not a dict
        import json
        import re
        
        result_str = str(result)
        # Look for JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\n(.*?)\n```', result_str, re.DOTALL)
        if json_match:
            context_data = json.loads(json_match.group(1))
        else:
            # Try to parse the whole string
            try:
                context_data = json.loads(result_str)
            except:
                # Last resort: create a simple context dict
                context_data = {
                    "key_context_points": [],
                    "follow_up_recommendations": [],
                    "context_summary": result_str[:300]  # Truncate if needed
                }
    
    return context_data

def get_relevant_summaries_by_topic(user_id, topic_keywords, max_summaries=2):
    """
    Get session summaries most relevant to specific topics
    
    Args:
        user_id: User ID
        topic_keywords: List of topic keywords to search for
        max_summaries: Maximum number of summaries to return
        
    Returns:
        List of relevant session summary documents
    """
    # Convert keywords to regex pattern for search
    # This is a simplistic approach - in production, you might use vector search
    keyword_patterns = [{"summary_data.main_topics": {"$regex": keyword, "$options": "i"}} 
                     for keyword in topic_keywords]
    
    # Search for summaries that match any of the keywords
    query = {
        "user_id": user_id,
        "$or": keyword_patterns
    }
    
    summaries = list(db.session_summaries.find(
        query,
        {"session_id": 1, "summary_data": 1, "created_at": 1}
    ).sort("created_at", -1).limit(max_summaries))
    
    return summaries

def prepare_contextual_followup_task(consolidated_context, current_query):
    """
    Create a task for generating follow-up suggestions based on context
    
    Args:
        consolidated_context: Consolidated context dictionary
        current_query: Current user query
    """
    
    return Task(
        description=f"""
        Based on the user's current query and their previous session context, generate relevant follow-up suggestions.
        
        Current user query:
        "{current_query}"
        
        Previous session context:
        {consolidated_context}
        
        Generate 2-3 relevant follow-up questions or suggestions that would:
        1. Address any unresolved topics from previous sessions
        2. Help the user progress in their career guidance journey
        3. Feel natural and relevant to the current conversation
        
        Format your response as JSON with these fields:
        {{
            "follow_up_suggestions": [
                {{
                    "suggestion": "Your suggestion or question here",
                    "rationale": "Brief explanation of why this is relevant"
                }},
                ...
            ]
        }}
        
        Keep your suggestions concise, natural-sounding, and directly relevant to the current interaction.
        """,
        agent=create_context_manager_agent(api_key),
        expected_output="A JSON object with follow-up suggestions and rationales."
    )

def generate_contextual_followups(user_id, current_query, consolidated_context=None):
    """
    Generate contextual follow-up suggestions based on previous context
    
    Args:
        user_id: User ID
        current_query: Current user query
        consolidated_context: Optional pre-generated consolidated context
        
    Returns:
        List of follow-up suggestions
    """
    # Get consolidated context if not provided
    if not consolidated_context:
        consolidated_context = generate_consolidated_context(user_id, current_query=current_query)
    
    # If context is empty or minimal, return empty suggestions
    if not consolidated_context or consolidated_context.get("context_summary", "") == "No previous session context available.":
        return []
    
    # Create and execute follow-up suggestion task
    context_agent = create_context_manager_agent(api_key)
    followup_task = prepare_contextual_followup_task(consolidated_context, current_query)
    
    followup_crew = Crew(
        agents=[context_agent],
        tasks=[followup_task],
        verbose=False,
        process=Process.sequential
    )
    
    result = followup_crew.kickoff()
    
    # Extract JSON from result
    try:
        # Try to parse as JSON directly
        followup_data = dict(result)
    except:
        # Fall back to string parsing if result is not a dict
        import json
        import re
        
        result_str = str(result)
        # Look for JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\n(.*?)\n```', result_str, re.DOTALL)
        if json_match:
            followup_data = json.loads(json_match.group(1))
        else:
            # Try to parse the whole string
            try:
                followup_data = json.loads(result_str)
            except:
                # Last resort: create a simple followup dict
                followup_data = {
                    "follow_up_suggestions": []
                }
    
    return followup_data.get("follow_up_suggestions", [])

def create_context_enhanced_prompt(base_prompt, user_id, current_query=None, current_session_id=None):
    """
    Create a context-enhanced prompt by incorporating relevant previous session context
    
    Args:
        base_prompt: Base prompt text
        user_id: User ID
        current_query: Optional current user query
        current_session_id: Optional current session ID
        
    Returns:
        Enhanced prompt with contextual information
    """
    # Generate consolidated context
    context = generate_consolidated_context(
        user_id, 
        current_session_id=current_session_id, 
        current_query=current_query
    )
    
    # If no meaningful context is available, return the base prompt
    if context.get("context_summary", "") == "No previous session context available.":
        return base_prompt
    
    # Format context points
    key_points = "\n".join([f"- {point}" for point in context.get("key_context_points", [])])
    ongoing_interests = ", ".join(context.get("ongoing_interests", []))
    previous_recommendations = "\n".join([f"- {rec}" for rec in context.get("previous_recommendations", [])])
    follow_ups = "\n".join([f"- {follow}" for follow in context.get("follow_up_recommendations", [])])
    
    # Construct context-enhanced prompt
    enhanced_prompt = f"""
{base_prompt}

Previous Session Context:
{context.get("context_summary", "")}

Key points from previous sessions:
{key_points}

Ongoing career interests: {ongoing_interests}

Previous recommendations:
{previous_recommendations}

Suggested follow-up points:
{follow_ups}

Please use this context to provide a personalized and continuous experience for the user.
"""
    
    return enhanced_prompt

def get_unresolved_questions(user_id, limit=3):
    """
    Get unresolved questions or topics from previous sessions
    
    Args:
        user_id: User ID
        limit: Maximum number of unresolved questions to return
        
    Returns:
        List of unresolved question dictionaries
    """
    # Get recent summaries
    summaries = get_recent_session_summaries(user_id, limit=5)
    
    # Extract follow-up points from summaries
    unresolved = []
    for summary in summaries:
        summary_data = summary.get("summary_data", {})
        
        # Extract follow-up points
        follow_ups = summary_data.get("follow_ups", [])
        session_date = summary.get("created_at", datetime.now(timezone.utc))
        
        # Add each follow-up as an unresolved question
        for follow_up in follow_ups:
            unresolved.append({
                "question": follow_up,
                "session_date": session_date.strftime("%Y-%m-%d"),
                "days_since": (datetime.now(timezone.utc) - session_date).days
            })
            
    # Sort by recency and return limited number
    unresolved.sort(key=lambda x: x["days_since"])
    return unresolved[:limit]

def detect_topic_continuity(current_query, user_id):
    """
    Detect if the current query continues a topic from previous sessions
    
    Args:
        current_query: Current user query
        user_id: User ID
        
    Returns:
        Continuity information dictionary or None if no continuity detected
    """
    # Get consolidated context
    context = generate_consolidated_context(user_id, current_query=current_query)
    
    # If no context, return None
    if context.get("context_summary", "") == "No previous session context available.":
        return None
    
    # Create and execute topic continuity detection task
    context_agent = create_context_manager_agent(api_key)
    
    continuity_task = Task(
        description=f"""
        Determine if the user's current query continues a topic from previous sessions.
        
        Current user query:
        "{current_query}"
        
        Previous session topics and interests:
        Key points: {context.get("key_context_points", [])}
        Ongoing interests: {context.get("ongoing_interests", [])}
        
        Assess if the current query is:
        1. Continuing a previous topic (strong continuity)
        2. Related to a previous topic but taking a new direction (moderate continuity)
        3. Introducing a new topic (no continuity)
        
        Format your response as JSON with these fields:
        {{
            "continuity_level": "strong|moderate|none",
            "related_previous_topic": "the topic this relates to or null",
            "explanation": "brief explanation of the continuity assessment"
        }}
        """,
        agent=context_agent,
        expected_output="A JSON object with topic continuity assessment."
    )
    
    continuity_crew = Crew(
        agents=[context_agent],
        tasks=[continuity_task],
        verbose=False,
        process=Process.sequential
    )
    
    result = continuity_crew.kickoff()
    
    # Extract JSON from result
    try:
        # Try to parse as JSON directly
        continuity_data = dict(result)
    except:
        # Fall back to string parsing if result is not a dict
        import json
        import re
        
        result_str = str(result)
        # Look for JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\n(.*?)\n```', result_str, re.DOTALL)
        if json_match:
            continuity_data = json.loads(json_match.group(1))
        else:
            # Try to parse the whole string
            try:
                continuity_data = json.loads(result_str)
            except:
                # Return None if parsing fails
                return None
    
    # Return None if no continuity detected
    if continuity_data.get("continuity_level") == "none":
        return None
        
    return continuity_data

def create_session_introduction(user_id):
    """
    Create a personalized session introduction based on previous interactions
    
    Args:
        user_id: User ID
        
    Returns:
        Personalized introduction text
    """
    # Get consolidated context
    context = generate_consolidated_context(user_id)
    
    # Get unresolved questions
    unresolved = get_unresolved_questions(user_id, limit=1)
    
    # If no previous context, return generic introduction
    if context.get("context_summary", "") == "No previous session context available.":
        return "Welcome to your career guidance session. How can I help you today?"
    
    # Create and execute introduction generation task
    context_agent = create_context_manager_agent(api_key)
    
    intro_task = Task(
        description=f"""
        Create a personalized introduction for a returning user based on their previous sessions.
        
        Previous session context:
        {context.get("context_summary", "")}
        
        Ongoing interests: {', '.join(context.get("ongoing_interests", []))}
        
        Unresolved questions: {unresolved[0]['question'] if unresolved else "None"}
        
        Create a warm, personalized welcome that:
        1. Acknowledges their return
        2. References their previous topics or interests
        3. Offers to continue the conversation or explore new areas
        4. Is warm and conversational in tone
        
        Keep the introduction concise (2-3 sentences).
        """,
        agent=context_agent,
        expected_output="A personalized session introduction."
    )
    
    intro_crew = Crew(
        agents=[context_agent],
        tasks=[intro_task],
        verbose=False,
        process=Process.sequential
    )
    
    return intro_crew.kickoff()