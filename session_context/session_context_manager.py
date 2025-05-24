"""
Enhanced Session Context Manager

This agent retrieves and consolidates summaries from previous sessions to provide
contextual information for the current session. If summaries don't exist, it will
automatically generate them using the session summarizer agent in batch mode.

Key improvements:
1. Batch summarization of multiple sessions at once for efficiency
2. Prioritizes the most recent sessions without summaries
3. Parallel processing capabilities for faster execution
4. Better error handling and recovery
"""
import json
import re
import os
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from crewai import Agent, Task, Crew, Process
from langchain_community.chat_models import ChatLiteLLM

# Use your existing database functions
from backend.database import db
import streamlit as st

# Import session summarizer functions
from session_summarizer_agent import (
    create_summarizer_agent, 
    summarize_session_task, 
    save_session_summary
)

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

def get_session_data_for_summarization(session_id):
    """
    Get raw session data (messages) for summarization
    
    Args:
        session_id: Session ID to retrieve
        
    Returns:
        Dict with session data or None if session not found
    """
    try:
        session = db["chat_sessions"].find_one({"_id": ObjectId(session_id)})
        if session and "messages" in session and len(session["messages"]) > 0:
            return {
                "session_id": str(session["_id"]),
                "messages": session["messages"],
                "created_at": session.get("created_at"),
                "updated_at": session.get("updated_at")
            }
        return None
    except Exception as e:
        print(f"Error retrieving session data for {session_id}: {e}")
        return None

def generate_single_session_summary(user_id, session_data):
    """
    Generate a summary for a single session
    
    Args:
        user_id: User ID
        session_data: Dict containing session data from get_session_data_for_summarization
        
    Returns:
        Dict with summary_id and session_id if successful, None otherwise
    """
    try:
        session_id = session_data["session_id"]
        messages = session_data["messages"]
        
        if not messages or len(messages) == 0:
            print(f"No messages found for session {session_id}")
            return None
        
        # Get user profile for context (optional)
        user_profile = None
        try:
            user_data = db["users"].find_one({"_id": ObjectId(user_id)})
            if user_data:
                user_profile = {
                    "name": user_data.get("name", ""),
                    "background": user_data.get("background", ""),
                    "interests": user_data.get("interests", [])
                }
        except:
            pass
        
        # Create and execute summarization task
        summary_agent = create_summarizer_agent(api_key)
        summary_task = summarize_session_task(
            messages, 
            user_profile, 
            session_id, 
            is_incremental=False
        )
        
        summary_crew = Crew(
            agents=[summary_agent],
            tasks=[summary_task],
            verbose=False,
            process=Process.sequential
        )
        
        result = summary_crew.kickoff()
        
        # Extract JSON from result
        try:
            # Try to parse as JSON directly
            if isinstance(result, dict):
                summary_data = result
            else:
                # Fall back to string parsing if result is not a dict
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
                            "summary_text": result_str[:500] if result_str else "Session completed successfully",
                            "raw_result": result_str
                        }
        except Exception as parse_error:
            print(f"Error parsing summary for session {session_id}: {parse_error}")
            summary_data = {
                "main_topics": ["Session summary"],
                "summary_text": "Summary generated but parsing encountered issues",
                "parse_error": str(parse_error)
            }
        
        # Save the summary to MongoDB
        summary_id = save_session_summary(
            user_id, 
            session_id, 
            summary_data, 
            is_incremental=False
        )
        
        print(f"Generated summary for session {session_id}: {summary_id}")
        return {
            "summary_id": summary_id,
            "session_id": session_id,
            "summary_data": summary_data
        }
        
    except Exception as e:
        print(f"Error generating summary for session {session_data.get('session_id', 'unknown')}: {e}")
        return None

def batch_generate_session_summaries(user_id, sessions_to_summarize, max_workers=3):
    """
    Generate summaries for multiple sessions in batch mode with parallel processing
    
    Args:
        user_id: User ID
        sessions_to_summarize: List of session data dicts
        max_workers: Maximum number of parallel workers
        
    Returns:
        List of successfully generated summaries
    """
    if not sessions_to_summarize:
        return []
    
    print(f"Batch generating summaries for {len(sessions_to_summarize)} sessions...")
    generated_summaries = []
    
    # Use ThreadPoolExecutor for parallel processing (limited to avoid rate limits)
    with ThreadPoolExecutor(max_workers=min(max_workers, len(sessions_to_summarize))) as executor:
        # Submit all summarization tasks
        future_to_session = {
            executor.submit(generate_single_session_summary, user_id, session_data): session_data
            for session_data in sessions_to_summarize
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_session):
            session_data = future_to_session[future]
            try:
                result = future.result()
                if result:
                    generated_summaries.append({
                        "session_id": result["session_id"],
                        "summary_data": result["summary_data"],
                        "created_at": datetime.now(timezone.utc)
                    })
                    print(f"✓ Summary completed for session {result['session_id']}")
                else:
                    print(f"✗ Failed to generate summary for session {session_data['session_id']}")
            except Exception as e:
                print(f"✗ Exception during summary generation for session {session_data['session_id']}: {e}")
    
    print(f"Batch generation complete: {len(generated_summaries)}/{len(sessions_to_summarize)} successful")
    return generated_summaries

def get_recent_session_summaries(user_id, limit=3, exclude_session_id=None):
    """
    Get recent session summaries for a user, generating missing summaries in batch
    
    Args:
        user_id: User ID
        limit: Maximum number of summaries to retrieve
        exclude_session_id: Optional session ID to exclude (current session)
    
    Returns:
        List of session summary documents
    """
    print(f"Getting recent session summaries for user {user_id} (limit: {limit})")
    
    # First, try to get existing summaries
    query = {"user_id": user_id}
    if exclude_session_id:
        query["session_id"] = {"$ne": exclude_session_id}
    
    existing_summaries = list(db.session_summaries.find(
        query,
        {"session_id": 1, "summary_data": 1, "created_at": 1}
    ).sort("created_at", -1).limit(limit))
    
    print(f"Found {len(existing_summaries)} existing summaries")
    
    # If we have enough summaries, return them
    if len(existing_summaries) >= limit:
        return existing_summaries
    
    # Otherwise, we need to generate missing summaries
    needed_count = limit - len(existing_summaries)
    print(f"Need to generate {needed_count} additional summaries")
    
    # Get recent chat sessions that don't have summaries
    sessions_query = {"user_id": user_id}
    if exclude_session_id:
        sessions_query["_id"] = {"$ne": ObjectId(exclude_session_id)}
    
    # Get session IDs that already have summaries
    existing_session_ids = {summary["session_id"] for summary in existing_summaries}
    
    # Get recent sessions, excluding those with existing summaries
    recent_sessions_cursor = db["chat_sessions"].find(
        sessions_query,
        {"_id": 1, "created_at": 1, "updated_at": 1, "messages": 1}
    ).sort("updated_at", -1).limit(needed_count * 2)  # Get more than needed to filter
    
    # Collect sessions that need summarization
    sessions_to_summarize = []
    for session in recent_sessions_cursor:
        session_id = str(session["_id"])
        if (session_id not in existing_session_ids and 
            session.get("messages") and 
            len(session["messages"]) > 0):
            
            session_data = get_session_data_for_summarization(session_id)
            if session_data:
                sessions_to_summarize.append(session_data)
                
                # Stop when we have enough sessions to summarize
                if len(sessions_to_summarize) >= needed_count:
                    break
    
    print(f"Found {len(sessions_to_summarize)} sessions that need summarization")
    
    # Generate summaries in batch if we have sessions to summarize
    newly_generated = []
    if sessions_to_summarize:
        newly_generated = batch_generate_session_summaries(
            user_id, 
            sessions_to_summarize[:needed_count]
        )
    
    # Combine existing and newly generated summaries
    all_summaries = existing_summaries + newly_generated
    
    # Sort by creation date and return the most recent ones
    all_summaries.sort(key=lambda x: x["created_at"], reverse=True)
    final_summaries = all_summaries[:limit]
    
    print(f"Returning {len(final_summaries)} total summaries")
    return final_summaries

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
    print(f"Generating consolidated context for user {user_id}")
    
    # Get recent session summaries (auto-generating missing ones in batch)
    summaries = get_recent_session_summaries(
        user_id, 
        limit=limit, 
        exclude_session_id=current_session_id
    )
    
    # If no previous summaries, return empty context
    if not summaries:
        return {
            "key_context_points": [],
            "ongoing_interests": [],
            "previous_recommendations": [],
            "follow_up_recommendations": [],
            "context_summary": "No previous session context available."
        }
    
    print(f"Consolidating context from {len(summaries)} session summaries")
    
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
        if isinstance(result, dict):
            context_data = result
        else:
            # Fall back to string parsing if result is not a dict
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
                        "ongoing_interests": [],
                        "previous_recommendations": [],
                        "follow_up_recommendations": [],
                        "context_summary": result_str[:150] if result_str else "Context generation completed"
                    }
    except Exception as e:
        print(f"Error parsing consolidated context: {e}")
        context_data = {
            "key_context_points": [],
            "ongoing_interests": [],
            "previous_recommendations": [],
            "follow_up_recommendations": [],
            "context_summary": "Context consolidation completed but parsing encountered issues"
        }
    
    print("Consolidated context generated successfully")
    return context_data

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
        if isinstance(result, dict):
            followup_data = result
        else:
            # Fall back to string parsing if result is not a dict
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
    except Exception as e:
        print(f"Error parsing follow-up suggestions: {e}")
        followup_data = {
            "follow_up_suggestions": []
        }
    
    return followup_data.get("follow_up_suggestions", [])

def test_enhanced_context_manager():
    """Test the enhanced session context manager functionality"""
    
    # Test data - replace with actual user ID from your database
    test_user_id = "6809c002a03a7a1e240ab91e"  # From your profile data
    test_session_id = "6809c3daa03a7a1e240ab91f"  # Example session ID
    test_query = "I want to know about remote job opportunities in AI development"
    
    print("=== Testing Enhanced Session Context Manager (Batch Mode) ===\n")
    
    # Test 1: Get recent session summaries with batch generation
    print("1. Testing batch get_recent_session_summaries...")
    try:
        summaries = get_recent_session_summaries(test_user_id, limit=3)
        print(f"   Retrieved {len(summaries)} session summaries")
        for i, summary in enumerate(summaries):
            print(f"   Summary {i+1}: Session {summary['session_id']} - {summary['created_at']}")
            topics = summary['summary_data'].get('main_topics', [])
            print(f"   Topics: {topics}")
    except Exception as e:
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # Test 2: Generate consolidated context
    print("2. Testing generate_consolidated_context...")
    try:
        context = generate_consolidated_context(
            test_user_id, 
            current_session_id=test_session_id,
            current_query=test_query
        )
        print("   Generated context:")
        print(f"   - Key context points: {context.get('key_context_points', [])}")
        print(f"   - Ongoing interests: {context.get('ongoing_interests', [])}")
        print(f"   - Previous recommendations: {context.get('previous_recommendations', [])}")
        print(f"   - Context summary: {context.get('context_summary', 'N/A')}")
    except Exception as e:
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        context = None
    
    print()
    
    # Test 3: Generate contextual follow-ups
    print("3. Testing generate_contextual_followups...")
    try:
        followups = generate_contextual_followups(
            test_user_id,
            test_query,
            consolidated_context=context
        )
        print("   Generated follow-up suggestions:")
        for i, suggestion in enumerate(followups):
            print(f"   {i+1}. {suggestion.get('suggestion', 'N/A')}")
            print(f"      Rationale: {suggestion.get('rationale', 'N/A')}")
    except Exception as e:
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Enhanced Batch Test Complete ===")

if __name__ == "__main__":
    print("Enhanced Session Context Manager (Batch Mode) is ready!")
    print("Running test...")
    test_enhanced_context_manager()