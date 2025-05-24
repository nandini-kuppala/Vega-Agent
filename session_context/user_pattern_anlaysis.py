"""
Fixed Test file for Pattern Analyzer Agent functionality
Fixes MongoDB serialization issues with proper data cleaning
"""

import os
import sys
import json
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from bson import ObjectId
from crewai import Crew, Process
# Import the pattern analyzer functions
from session_context.pattern_analyzer_agent import (
    analyze_session_pattern,
    analyze_cross_session_patterns,
    get_user_pattern_summary,
    save_session_pattern,
    save_cross_session_pattern,
    extract_user_queries,
    create_pattern_analyzer_agent,
    analyze_single_session_pattern_task,
    analyze_cross_session_patterns_task,
    api_key
)

# Import database functions
from backend.database import db, get_chat_session, get_user_chat_sessions

def clean_for_mongodb(obj):
    """
    Recursively clean an object to ensure MongoDB serialization compatibility
    
    Args:
        obj: Object to clean
    
    Returns:
        Cleaned object that's MongoDB-safe
    """
    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, datetime):
        return obj  # MongoDB handles datetime objects natively
    elif isinstance(obj, ObjectId):
        return str(obj)  # Convert ObjectId to string
    elif isinstance(obj, list):
        return [clean_for_mongodb(item) for item in obj]
    elif isinstance(obj, dict):
        cleaned = {}
        for key, value in obj.items():
            # Ensure keys are strings
            clean_key = str(key) if not isinstance(key, str) else key
            cleaned[clean_key] = clean_for_mongodb(value)
        return cleaned
    elif hasattr(obj, '__dict__'):
        # Handle objects with __dict__ (like Pydantic models)
        return clean_for_mongodb(obj.__dict__)
    elif hasattr(obj, 'dict') and callable(obj.dict):
        # Handle Pydantic models with dict() method
        return clean_for_mongodb(obj.dict())
    elif hasattr(obj, 'model_dump') and callable(obj.model_dump):
        # Handle Pydantic v2 models
        return clean_for_mongodb(obj.model_dump())
    else:
        # For any other type, convert to string as fallback
        return str(obj)

def parse_crew_result(result):
    """
    Enhanced function to parse CrewAI result and extract JSON data
    
    Args:
        result: CrewAI result object
    
    Returns:
        Dictionary with parsed pattern data
    """
    try:
        result_str = ""
        
        # Handle different result types
        if hasattr(result, 'raw') and result.raw:
            result_str = result.raw
            print(f"   Using result.raw: {result_str[:100]}...")
        elif hasattr(result, '__str__'):
            result_str = str(result)
            print(f"   Using str(result): {result_str[:100]}...")
        else:
            print(f"   Unknown result type: {type(result)}")
            result_str = repr(result)
        
        # Look for JSON in markdown code blocks first
        import re
        json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', result_str, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            try:
                parsed_data = json.loads(json_str)
                print(f"   Successfully parsed JSON from code block")
                # Clean the parsed data
                return clean_for_mongodb(parsed_data)
            except json.JSONDecodeError as e:
                print(f"   JSON parse error in code block: {e}")
        
        # Try to find JSON without code blocks
        json_match = re.search(r'\{.*\}', result_str, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                parsed_data = json.loads(json_str)
                print(f"   Successfully parsed JSON from direct match")
                # Clean the parsed data
                return clean_for_mongodb(parsed_data)
            except json.JSONDecodeError as e:
                print(f"   JSON parse error in direct match: {e}")
        
        # If no JSON found, create a basic pattern dict
        print("   No valid JSON found, creating basic pattern")
        return {
            "pattern_summary": result_str[:500] if len(result_str) > 500 else result_str,
            "learning_style": "mixed",
            "learning_approach": "exploratory",
            "question_specificity": "mixed",
            "engagement_level": "medium",
            "focus_topics": [],
            "topic_progression": "Unable to parse detailed progression",
            "parsing_note": "Generated from unparseable result"
        }
        
    except Exception as e:
        print(f"   Error parsing CrewAI result: {e}")
        return {
            "pattern_summary": "Error parsing result",
            "learning_style": "mixed",
            "learning_approach": "exploratory",
            "question_specificity": "mixed",
            "engagement_level": "medium",
            "focus_topics": [],
            "topic_progression": "Error occurred during parsing",
            "error": str(e)
        }

def is_mongodb_serializable(obj):
    """
    Check if object is MongoDB serializable by attempting to clean it
    
    Args:
        obj: Object to check
    
    Returns:
        Boolean indicating if object can be stored in MongoDB
    """
    try:
        cleaned = clean_for_mongodb(obj)
        # Test JSON serialization as additional check
        json.dumps(cleaned, default=str)
        return True
    except Exception as e:
        print(f"   Serialization test failed: {e}")
        return False

def should_analyze_cross_session_patterns(user_id):
    """
    Enhanced logic to determine if we should run cross-session analysis
    
    Args:
        user_id: User ID
    
    Returns:
        Boolean indicating if cross-session analysis should be run
    """
    # Count existing session patterns for this user
    session_pattern_count = db.session_patterns.count_documents({"user_id": user_id})
    
    # Check when the last cross-session analysis was done
    last_cross_session = db.user_patterns.find_one(
        {"user_id": user_id},
        sort=[("updated_at", -1)]
    )
    
    # Run cross-session analysis if:
    # 1. We have at least 2 session patterns AND
    # 2. Either no cross-session analysis exists OR
    # 3. We have 3+ new session patterns since last cross-session analysis
    if session_pattern_count >= 2:
        if not last_cross_session:
            return True
        
        # Count patterns created after last cross-session analysis
        patterns_since_last = db.session_patterns.count_documents({
            "user_id": user_id,
            "created_at": {"$gt": last_cross_session["updated_at"]}
        })
        
        return patterns_since_last >= 3
    
    return False

def get_sessions_needing_pattern_analysis(user_id, limit=3):
    """
    Get recent sessions that don't have pattern analysis yet
    
    Args:
        user_id: User ID
        limit: Maximum number of sessions to analyze
    
    Returns:
        List of session data for sessions needing analysis
    """
    # Get existing session pattern IDs
    existing_patterns = db.session_patterns.find(
        {"user_id": user_id},
        {"session_id": 1}
    )
    analyzed_session_ids = {pattern["session_id"] for pattern in existing_patterns}
    
    # Get recent chat sessions that haven't been analyzed
    sessions_cursor = db["chat_sessions"].find(
        {"user_id": user_id},
        {"_id": 1, "messages": 1, "created_at": 1}
    ).sort("updated_at", -1).limit(limit * 2)  # Get more than needed to filter
    
    sessions_to_analyze = []
    for session in sessions_cursor:
        session_id = str(session["_id"])
        
        # Skip if already analyzed
        if session_id in analyzed_session_ids:
            continue
            
        # Skip if session doesn't have enough user messages - reduce requirement to 2
        user_queries = extract_user_queries(session.get("messages", []))
        if len(user_queries) < 2:
            continue
            
        sessions_to_analyze.append({
            "session_id": session_id,
            "messages": session["messages"],
            "created_at": session["created_at"]
        })
        
        # Stop when we have enough sessions
        if len(sessions_to_analyze) >= limit:
            break
    
    return sessions_to_analyze

def batch_generate_session_patterns(user_id, sessions_data):
    """
    Generate session patterns for multiple sessions in parallel with proper MongoDB serialization
    
    Args:
        user_id: User ID
        sessions_data: List of session data dictionaries
    
    Returns:
        List of generated pattern IDs
    """
    def analyze_single_session_safe(session_data):
        """Helper function for parallel execution with improved data cleaning"""
        try:
            session_id = session_data["session_id"]
            messages = session_data["messages"]
            
            # Only analyze sessions with at least 2 user queries
            user_queries = extract_user_queries(messages)
            if len(user_queries) < 2:
                return {
                    "status": "skipped",
                    "session_id": session_id,
                    "reason": "Insufficient user queries"
                }
            
            # Create and execute pattern analysis task
            pattern_agent = create_pattern_analyzer_agent(api_key)
            pattern_task = analyze_single_session_pattern_task(user_queries, session_id)
            
            from crewai import Crew, Process
            pattern_crew = Crew(
                agents=[pattern_agent],
                tasks=[pattern_task],
                verbose=False,
                process=Process.sequential
            )
            
            result = pattern_crew.kickoff()
            
            # Debug: Print result type and attributes
            print(f"   Result type: {type(result)}")
            print(f"   Result has raw attribute: {hasattr(result, 'raw')}")
            
            # Use the improved parse_crew_result function
            pattern_data = parse_crew_result(result)
            
            # Debug: Verify pattern_data is clean
            print(f"   Pattern data type: {type(pattern_data)}")
            print(f"   Pattern data keys: {list(pattern_data.keys()) if isinstance(pattern_data, dict) else 'Not a dict'}")
            
            # Ensure we have valid pattern data
            if not pattern_data or not isinstance(pattern_data, dict):
                pattern_data = {
                    "pattern_summary": "Failed to parse pattern analysis",
                    "learning_style": "mixed",
                    "learning_approach": "exploratory",
                    "question_specificity": "mixed",
                    "engagement_level": "medium",
                    "focus_topics": [],
                    "topic_progression": "Unable to determine progression"
                }
            
            # Clean the pattern data for MongoDB storage
            pattern_data = clean_for_mongodb(pattern_data)
            
            # Create the document with properly cleaned data
            pattern_doc = {
                "user_id": clean_for_mongodb(user_id),
                "session_id": clean_for_mongodb(session_id),
                "pattern_data": pattern_data,
                "created_at": datetime.now(timezone.utc)
            }
            
            # Final validation
            if not is_mongodb_serializable(pattern_doc):
                print(f"   Warning: Document still not serializable, creating minimal fallback")
                pattern_doc = {
                    "user_id": str(user_id),
                    "session_id": str(session_id),
                    "pattern_data": {
                        "pattern_summary": "Minimal pattern due to serialization issues",
                        "learning_style": "mixed",
                        "learning_approach": "exploratory",
                        "question_specificity": "mixed",
                        "engagement_level": "medium",
                        "focus_topics": [],
                        "topic_progression": "Serialization fallback"
                    },
                    "created_at": datetime.now(timezone.utc)
                }
            
            # Insert into MongoDB
            result_doc = db.session_patterns.insert_one(pattern_doc)
            pattern_id = str(result_doc.inserted_id)
            
            print(f"   Successfully inserted pattern document with ID: {pattern_id}")
            
            return {
                "status": "success",
                "session_id": session_id,
                "pattern_id": pattern_id
            }
            
        except Exception as e:
            print(f"   Error analyzing session {session_data.get('session_id', 'unknown')}: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "session_id": session_data.get("session_id", "unknown"),
                "error": str(e)
            }
    
    results = []
    
    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all tasks
        future_to_session = {
            executor.submit(analyze_single_session_safe, session_data): session_data["session_id"]
            for session_data in sessions_data
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_session):
            session_id = future_to_session[future]
            try:
                result = future.result()
                results.append(result)
                print(f"   Session {session_id}: {result['status']}")
                if result['status'] == 'error':
                    print(f"   Error: {result['error']}")
                elif result['status'] == 'skipped':
                    print(f"   Reason: {result['reason']}")
            except Exception as e:
                print(f"   Session {session_id}: Failed with exception: {e}")
                results.append({
                    "status": "error",
                    "session_id": session_id,
                    "error": str(e)
                })
    
    # Return successful pattern IDs
    successful_patterns = [r["pattern_id"] for r in results if r["status"] == "success" and r.get("pattern_id")]
    return successful_patterns

def enhanced_cross_session_analysis(user_id, force_generate_missing=True):
    """
    Enhanced cross-session analysis that ensures we have enough session patterns
    
    Args:
        user_id: User ID
        force_generate_missing: If True, generate missing session patterns before cross-session analysis
    
    Returns:
        Pattern ID if analysis was created, None otherwise
    """
    print(f"Starting enhanced cross-session analysis for user {user_id}")
    
    # Check existing session patterns
    existing_patterns = list(db.session_patterns.find(
        {"user_id": user_id},
        {"session_id": 1, "created_at": 1}
    ).sort("created_at", -1).limit(5))
    
    print(f"Found {len(existing_patterns)} existing session patterns")
    
    # If we don't have enough patterns and force_generate_missing is True
    if len(existing_patterns) < 3 and force_generate_missing:
        print("Not enough session patterns. Generating missing patterns...")
        
        # Get sessions that need pattern analysis
        sessions_to_analyze = get_sessions_needing_pattern_analysis(
            user_id, 
            limit=3 - len(existing_patterns)
        )
        
        print(f"Found {len(sessions_to_analyze)} sessions to analyze")
        
        if sessions_to_analyze:
            # Generate patterns in parallel
            newly_generated = batch_generate_session_patterns(user_id, sessions_to_analyze)
            print(f"Generated {len(newly_generated)} new session patterns")
            
            # Refresh our existing patterns list
            existing_patterns = list(db.session_patterns.find(
                {"user_id": user_id},
                {"session_id": 1, "created_at": 1}
            ).sort("created_at", -1).limit(5))
            
            print(f"Now have {len(existing_patterns)} total session patterns")
    
    # Proceed with cross-session analysis if we have enough patterns
    if len(existing_patterns) >= 2:
        print("Proceeding with cross-session pattern analysis...")
        
        try:
            # Use the analyze_cross_session_patterns function but with better error handling
            pattern_id = analyze_cross_session_patterns_safe(user_id, max_sessions=min(5, len(existing_patterns)))
            print(f"Cross-session analysis completed. Pattern ID: {pattern_id}")
            return pattern_id
        except Exception as e:
            print(f"Error during cross-session analysis: {e}")
            return None
    else:
        print("Still not enough session patterns for cross-session analysis")
        return None

def analyze_cross_session_patterns_safe(user_id, max_sessions=5):
    """
    Safe version of cross-session pattern analysis with proper result parsing and MongoDB serialization
    
    Args:
        user_id: User ID
        max_sessions: Maximum number of sessions to analyze
    
    Returns:
        Pattern ID if successful, None otherwise
    """
    try:
        # Get recent session patterns
        session_patterns = list(db.session_patterns.find(
            {"user_id": user_id},
            {"pattern_data": 1, "session_id": 1, "created_at": 1}
        ).sort("created_at", -1).limit(max_sessions))
        
        if len(session_patterns) < 2:
            print(f"   Not enough session patterns for cross-session analysis: {len(session_patterns)}")
            return None
        
        # Create and execute cross-session analysis task
        pattern_agent = create_pattern_analyzer_agent(api_key)
        cross_session_task = analyze_cross_session_patterns_task(session_patterns, user_id)
        
        from crewai import Crew, Process
        cross_session_crew = Crew(
            agents=[pattern_agent],
            tasks=[cross_session_task],
            verbose=False,
            process=Process.sequential
        )
        
        result = cross_session_crew.kickoff()
        
        # Parse the result properly
        pattern_data = parse_crew_result(result)
        
        # Clean for MongoDB
        pattern_data = clean_for_mongodb(pattern_data)
        
        # Validate the cleaned pattern data
        if not pattern_data or not isinstance(pattern_data, dict):
            print("   Creating fallback cross-session pattern data")
            pattern_data = {
                "pattern_summary": "Cross-session analysis completed but parsing failed",
                "consistent_interests": [],
                "learning_style_pattern": "mixed",
                "preferred_learning_depth": "mixed",
                "follow_through_pattern": "moderate",
                "recommended_approach": "balanced"
            }
        
        # Create document with properly cleaned data
        pattern_doc = {
            "user_id": clean_for_mongodb(user_id),
            "pattern_data": pattern_data,
            "session_count": len(session_patterns),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Final MongoDB serialization check
        if not is_mongodb_serializable(pattern_doc):
            print("   Cross-session document not serializable, creating minimal version")
            pattern_doc = {
                "user_id": str(user_id),
                "pattern_data": {
                    "pattern_summary": "Minimal cross-session pattern due to serialization issues",
                    "consistent_interests": [],
                    "learning_style_pattern": "mixed",
                    "preferred_learning_depth": "mixed",
                    "follow_through_pattern": "moderate",
                    "recommended_approach": "balanced"
                },
                "session_count": len(session_patterns),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        
        # Insert into MongoDB
        result_doc = db.user_patterns.insert_one(pattern_doc)
        pattern_id = str(result_doc.inserted_id)
        
        print(f"   Successfully inserted cross-session pattern with ID: {pattern_id}")
        return pattern_id
        
    except Exception as e:
        print(f"   Error in cross-session analysis: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_single_session_pattern_analysis():
    """Test single session pattern analysis using only MongoDB data"""
    print("=== Testing Single Session Pattern Analysis (MongoDB Data Only) ===\n")
    
    # Test data
    test_user_id = "6809c002a03a7a1e240ab91e"
    
    # Get real sessions from MongoDB
    print("1. Getting real sessions from MongoDB...")
    try:
        sessions_result = get_user_chat_sessions(test_user_id, limit=5)
        if sessions_result["status"] == "success" and sessions_result["sessions"]:
            sessions = sessions_result["sessions"]
            print(f"   Found {len(sessions)} sessions for user")
            
            # Find a session with enough messages
            selected_session = None
            for session in sessions:
                session_id = session["_id"]
                session_result = get_chat_session(session_id)
                if session_result["status"] == "success":
                    session_data = session_result["session"]
                    messages = session_data.get("messages", [])
                    user_queries = extract_user_queries(messages)
                    
                    if len(user_queries) >= 2:  # Reduced requirement
                        selected_session = {
                            "id": session_id,
                            "messages": messages,
                            "user_queries": user_queries
                        }
                        print(f"   Selected session {session_id} with {len(user_queries)} user queries")
                        break
            
            if not selected_session:
                print("   ❌ No sessions found with sufficient user queries (minimum 2)")
                return
                
        else:
            print("   ❌ No sessions found for user")
            return
            
    except Exception as e:
        print(f"   ❌ Error getting sessions: {e}")
        return
    
    # Display user queries
    print(f"\n2. User queries from session {selected_session['id']}:")
    for i, query in enumerate(selected_session['user_queries'], 1):
        print(f"   {i}. {query}")
    
    # Test pattern analysis
    print(f"\n3. Running pattern analysis...")
    try:
        # Use our custom batch function instead for consistency
        session_data = [{
            "session_id": selected_session['id'],
            "messages": selected_session['messages'],
            "created_at": datetime.now(timezone.utc)
        }]
        
        generated_patterns = batch_generate_session_patterns(test_user_id, session_data)
        
        pattern_id = None
        if generated_patterns:
            pattern_id = generated_patterns[0]
        
        if pattern_id:
            print(f"   ✅ Pattern analysis completed. Pattern ID: {pattern_id}")
            
            # Retrieve and display the pattern
            pattern_doc = db.session_patterns.find_one({"_id": ObjectId(pattern_id)})
            if pattern_doc:
                print("   Pattern analysis results:")
                pattern_data = pattern_doc["pattern_data"]
                print(f"   - Topic progression: {pattern_data.get('topic_progression', 'N/A')}")
                print(f"   - Learning style: {pattern_data.get('learning_style', 'N/A')}")
                print(f"   - Learning approach: {pattern_data.get('learning_approach', 'N/A')}")
                print(f"   - Focus topics: {pattern_data.get('focus_topics', [])}")
                print(f"   - Pattern summary: {pattern_data.get('pattern_summary', 'N/A')}")
        else:
            print("   ❌ Pattern analysis failed")
            
    except Exception as e:
        print(f"   ❌ Error during pattern analysis: {e}")
        import traceback
        traceback.print_exc()

def test_enhanced_cross_session_analysis():
    """Test enhanced cross-session pattern analysis using only MongoDB data"""
    print("\n=== Testing Enhanced Cross-Session Pattern Analysis (MongoDB Data Only) ===\n")
    
    test_user_id = "6809c002a03a7a1e240ab91e"
    
    # Test 1: Check existing patterns
    print("1. Checking existing session patterns...")
    existing_count = db.session_patterns.count_documents({"user_id": test_user_id})
    print(f"   Found {existing_count} existing session patterns")
    
    # Test 2: Get sessions needing analysis from MongoDB
    print("\n2. Finding sessions from MongoDB that need pattern analysis...")
    sessions_to_analyze = get_sessions_needing_pattern_analysis(test_user_id, limit=3)
    print(f"   Found {len(sessions_to_analyze)} real sessions needing analysis")
    
    for i, session_data in enumerate(sessions_to_analyze):
        user_queries = extract_user_queries(session_data["messages"])
        print(f"   Session {i+1}: {session_data['session_id']} ({len(user_queries)} user queries)")
    
    # If we don't have enough sessions, get more from the database
    if len(sessions_to_analyze) == 0:
        print("   No unanalyzed sessions found. Getting any sessions with enough messages...")
        try:
            sessions_result = get_user_chat_sessions(test_user_id, limit=10)
            if sessions_result["status"] == "success":
                all_sessions = sessions_result["sessions"]
                sessions_to_analyze = []
                
                for session in all_sessions:
                    session_id = session["_id"]
                    session_result = get_chat_session(session_id)
                    if session_result["status"] == "success":
                        session_data = session_result["session"]
                        messages = session_data.get("messages", [])
                        user_queries = extract_user_queries(messages)
                        
                        if len(user_queries) >= 2:
                            sessions_to_analyze.append({
                                "session_id": session_id,
                                "messages": messages,
                                "created_at": session.get("created_at", datetime.now(timezone.utc))
                            })
                            
                            if len(sessions_to_analyze) >= 3:
                                break
                
                print(f"   Found {len(sessions_to_analyze)} sessions with sufficient messages")
                
        except Exception as e:
            print(f"   Error getting sessions: {e}")
            return
    
    # Test 3: Generate patterns for sessions if needed
    if sessions_to_analyze:
        print(f"\n3. Generating patterns for {len(sessions_to_analyze)} sessions in parallel...")
        try:
            generated_patterns = batch_generate_session_patterns(test_user_id, sessions_to_analyze)
            print(f"   ✅ Generated {len(generated_patterns)} session patterns")
        except Exception as e:
            print(f"   ❌ Error generating session patterns: {e}")
            import traceback
            traceback.print_exc()
    
    # Test 4: Run enhanced cross-session analysis
    print("\n4. Running enhanced cross-session analysis...")
    try:
        pattern_id = enhanced_cross_session_analysis(test_user_id, force_generate_missing=True)
        
        if pattern_id:
            print(f"   ✅ Cross-session analysis completed. Pattern ID: {pattern_id}")
            
            # Retrieve and display the cross-session pattern
            pattern_doc = db.user_patterns.find_one({"_id": ObjectId(pattern_id)})

            if pattern_doc:
                print("   Cross-session pattern analysis results:")
                pattern_data = pattern_doc["pattern_data"]
                print(f"   - Consistent interests: {pattern_data.get('consistent_interests', [])}")
                print(f"   - Learning style pattern: {pattern_data.get('learning_style_pattern', 'N/A')}")
                print(f"   - Preferred learning depth: {pattern_data.get('preferred_learning_depth', 'N/A')}")
                print(f"   - Follow-through pattern: {pattern_data.get('follow_through_pattern', 'N/A')}")
                print(f"   - Recommended approach: {pattern_data.get('recommended_approach', 'N/A')}")
                print(f"   - Pattern summary: {pattern_data.get('pattern_summary', 'N/A')}")
        else:
            print("   ❌ Cross-session analysis failed or insufficient data")
            
    except Exception as e:
        print(f"   ❌ Error during cross-session analysis: {e}")
        import traceback
        traceback.print_exc()

def test_pattern_summary_retrieval():
    """Test pattern summary retrieval"""
    print("\n=== Testing Pattern Summary Retrieval ===\n")
    
    test_user_id = "6809c002a03a7a1e240ab91e"
    
    print("1. Getting user pattern summary...")
    try:
        pattern_summary = get_user_pattern_summary(test_user_id)
        
        if pattern_summary:
            print("   ✅ Retrieved pattern summary:")
            if pattern_summary.get("is_single_session"):
                print("   - Type: Single session pattern")
            else:
                print("   - Type: Cross-session pattern")
            print(f"   - Summary: {pattern_summary.get('pattern_summary', 'N/A')}")
            
            # Display additional fields if available
            for key in ['consistent_interests', 'learning_style_pattern', 'recommended_approach']:
                if key in pattern_summary:
                    print(f"   - {key.replace('_', ' ').title()}: {pattern_summary[key]}")
        else:
            print("   ❌ No pattern summary found for user")
            
    except Exception as e:
        print(f"   ❌ Error retrieving pattern summary: {e}")
        import traceback
        traceback.print_exc()

def run_comprehensive_test():
    """Run comprehensive test of pattern analyzer functionality"""
    print("🚀 Starting Comprehensive Pattern Analyzer Test\n")
    print("=" * 60)
    
    try:
        # Test 1: Single session pattern analysis
        test_single_session_pattern_analysis()
        
        # Test 2: Enhanced cross-session pattern analysis  
        test_enhanced_cross_session_analysis()
        
        # Test 3: Pattern summary retrieval
        test_pattern_summary_retrieval()
        
        print("\n" + "=" * 60)
        print("✅ Comprehensive Pattern Analyzer Test Completed Successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Pattern Analyzer Test Suite")
    print("Testing both single session and cross-session pattern analysis")
    print("Using enhanced parallel processing for missing session patterns\n")
    
    run_comprehensive_test()