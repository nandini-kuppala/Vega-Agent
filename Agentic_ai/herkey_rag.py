## herkey_rag.py -- this file has all the functions to recommend jobs, events, sessions, communities from HerKey.com
import os
import json
from typing import Dict, List, Any
from datetime import datetime
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process

import google.generativeai as genai

from langchain_community.chat_models import ChatLiteLLM
# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Data paths
HERKEY_SESSIONS_PATH = "Agentic_ai/Herkey_data/herkey_sessions.json"
HERKEY_JOBS_PATH = "Agentic_ai/Herkey_data/herkey_jobs.json"
HERKEY_EVENTS_PATH = "Agentic_ai/Herkey_data/herkey_events.json"
HERKEY_GROUPS_PATH = "Agentic_ai/Herkey_data/herkey_groups.json"

# Load data files
def load_data(data_type=None):
    """
    Load data files required for recommendations
    
    Parameters:
    data_type (str, optional): Type of data to load ('sessions', 'jobs', 'events', 'groups')
                              If None, loads all data types
    
    Returns:
    dict: Dictionary containing the requested data
    """
    data = {}
    
    # Define paths dictionary for easier reference
    data_paths = {
        'sessions': HERKEY_SESSIONS_PATH,
        'jobs': HERKEY_JOBS_PATH,
        'events': HERKEY_EVENTS_PATH,
        'groups': HERKEY_GROUPS_PATH
    }
    
    # If no specific data type is requested, load all
    if data_type is None:
        types_to_load = data_paths.keys()
    else:
        # Ensure data_type is valid
        if data_type not in data_paths:
            raise ValueError(f"Invalid data_type: {data_type}. Must be one of {list(data_paths.keys())}")
        types_to_load = [data_type]
    
    # Load only the requested data types
    for type_name in types_to_load:
        try:
            with open(data_paths[type_name], 'r') as f:
                data[type_name] = json.load(f)
                print(f"Successfully loaded {type_name} data")
        except Exception as e:
            print(f"Error loading {type_name} data: {e}")
            data[type_name] = []
    
    return data
# Create agents
def create_profile_analyzer_agent():
    """Create an agent to analyze candidate profiles"""
    llm = ChatLiteLLM(
        model="gemini/gemini-1.5-flash",
        api_key=GEMINI_API_KEY,
        temperature=0.2
    )
    
    return Agent(
        role="Candidate Profile Analyzer",
        goal="Extract key career interests, skills, preferences, and growth areas from candidate profiles",
        backstory="""You are an expert career counselor with deep experience in understanding 
        candidate profiles. You can identify both explicit and implicit career aspirations, 
        skill levels, and preferences. You analyze profiles holistically to create a complete 
        picture of a candidate's career trajectory and needs.""",
        verbose=True,
        llm=llm
    )

def create_job_recommender_agent():
    """Create an agent to recommend jobs"""
    llm = ChatLiteLLM(
        model="gemini/gemini-1.5-flash",
        api_key=GEMINI_API_KEY,
        temperature=0.2
    )
    
    return Agent(
        role="Job Recommendation Specialist",
        goal="Match candidates with the most suitable job opportunities",
        backstory="""You are a specialized job recommendation expert with a deep understanding 
        of career paths and job requirements across industries. You excel at matching candidate 
        skills and preferences with job opportunities, considering both immediate fit and 
        growth potential. You understand nuances in job descriptions and can identify when a 
        candidate might be qualified despite not meeting all listed criteria.""",
        verbose=True,
        llm=llm
    )

def create_event_recommender_agent():
    """Create an agent to recommend events"""
    llm = ChatLiteLLM(
        model="gemini/gemini-1.5-flash",
        api_key=GEMINI_API_KEY,
        temperature=0.2
    )

    return Agent(
        role="Event Recommendation Specialist",
        goal="Find the most valuable events for a candidate's career growth",
        backstory="""You specialize in identifying events that align with a candidate's 
        career goals, interests, and development needs. You understand that different 
        events serve different purposes - networking, skill development, industry 
        knowledge - and can match candidates with events that will maximize their 
        career advancement at their current stage.""",
        verbose=True,
        llm=llm
    )

def create_session_recommender_agent():
    """Create an agent to recommend sessions"""
    llm = ChatLiteLLM(
        model="gemini/gemini-1.5-flash",
        api_key=GEMINI_API_KEY,
        temperature=0.2
    )
    
    return Agent(
        role="Learning Session Recommendation Specialist",
        goal="Identify the most beneficial learning sessions for candidate growth",
        backstory="""You are an educational guidance expert who can match candidates with 
        learning sessions that will best advance their career goals. You understand 
        the importance of session content, difficulty level, and relevance to the 
        candidate's current skills and aspirations. You can identify knowledge gaps 
        and recommend sessions that address them most effectively.""",
        verbose=True,
        llm=llm
    )

def create_community_recommender_agent():
    """Create an agent to recommend community groups"""
    llm = ChatLiteLLM(
        model="gemini/gemini-1.5-flash",
        api_key=GEMINI_API_KEY,
        temperature=0.2
    )
    
    return Agent(
        role="Community Group Recommendation Specialist",
        goal="Connect candidates with the most valuable community groups for their career",
        backstory="""You are a community building expert who understands the value of 
        professional networks and peer groups. You excel at identifying communities 
        that will provide candidates with valuable connections, learning opportunities, 
        and support systems aligned with their career goals. You understand the unique 
        value propositions of different community groups.""",
        verbose=True,
        llm=llm
    )

# Create tasks
def create_profile_analysis_task(profile_analyzer_agent, candidate_profile):
    """Create a task to analyze candidate profile"""
    return Task(
        description=f"""
        Analyze the following candidate profile to extract key insights:
        
        ```
        {json.dumps(candidate_profile, indent=2)}
        ```
        
        Provide a comprehensive analysis including:
        1. Primary skills and competency levels
        2. Career stage and trajectory
        3. Short and long-term career goals
        4. Work preferences (location, remote/in-person, etc.)
        5. Growth areas and learning needs
        6. Community engagement preferences
        
        Format your response as a structured JSON with clear sections for each area above.
        """,
        agent=profile_analyzer_agent,
        expected_output="A structured JSON with comprehensive candidate profile analysis"
    )
def create_job_recommendation_task(job_recommender_agent, candidate_analysis, jobs_data):
    """Create a task to recommend jobs with URLs"""
    return Task(
        description=f"""
        Based on the candidate profile analysis below, recommend the top 3 most suitable jobs from the provided job listings.
        
        Candidate Analysis:
        ```
        {json.dumps(candidate_analysis, indent=2)}
        ```
        
        Available Jobs:
        ```
        {json.dumps(jobs_data, indent=2)}
        ```
        
        For each recommendation, explain why it's a good match for the candidate's skills, experience, and career goals.
        Consider factors such as skill match, experience level, work type preferences, and alignment with career goals.
        
        Provide your recommendations in a JSON format with a 'recommendations' array containing objects with:
        1. job_title
        2. company
        3. job_url (extract from the data if available)
        4. match_score (1-100)
        5. match_explanation (detailed reasoning)
        6. growth_opportunity (how this job could help career advancement)
        """,
        agent=job_recommender_agent,
        expected_output="A JSON with top 3 job recommendations with match explanations and URLs"
    )

def create_event_recommendation_task(event_recommender_agent, candidate_analysis, events_data):
    """Create a task to recommend events with URLs"""
    return Task(
        description=f"""
        Based on the candidate profile analysis below, recommend the top 3 most valuable events from the provided event listings.
        
        Candidate Analysis:
        ```
        {json.dumps(candidate_analysis, indent=2)}
        ```
        
        Available Events:
        ```
        {json.dumps(events_data, indent=2)}
        ```
        
        For each recommendation, explain why this event would be particularly valuable for the candidate's career development.
        Consider factors such as event content, networking opportunities, skill development potential, and alignment with career goals.
        
        Provide your recommendations in a JSON format with a 'recommendations' array containing objects with:
        1. event_title
        2. event_date
        3. event_url (extract from the data if available)
        4. match_score (1-100)
        5. match_explanation (detailed reasoning)
        6. expected_benefits (specific career benefits from attendance)
        """,
        agent=event_recommender_agent,
        expected_output="A JSON with top 3 event recommendations with benefit explanations and URLs"
    )

def create_session_recommendation_task(session_recommender_agent, candidate_analysis, sessions_data):
    """Create a task to recommend learning sessions with URLs"""
    return Task(
        description=f"""
        Based on the candidate profile analysis below, recommend the top 3 most beneficial learning sessions from the provided session listings.
        
        Candidate Analysis:
        ```
        {json.dumps(candidate_analysis, indent=2)}
        ```
        
        Available Sessions:
        ```
        {json.dumps(sessions_data, indent=2)}
        ```
        
        For each recommendation, explain why this learning session would be particularly valuable for the candidate's skill development.
        Consider factors such as session content, skill relevance, difficulty level, and alignment with career goals.
        
        Provide your recommendations in a JSON format with a 'recommendations' array containing objects with:
        1. session_title
        2. session_date
        3. host
        4. session_url (extract from the data if available)
        5. match_score (1-100)
        6. match_explanation (detailed reasoning)
        7. learning_outcomes (specific skills or knowledge to be gained)
        """,
        agent=session_recommender_agent,
        expected_output="A JSON with top 3 session recommendations with learning outcome explanations and URLs"
    )

def create_community_recommendation_task(community_recommender_agent, candidate_analysis, groups_data):
    """Create a task to recommend community groups with URLs"""
    return Task(
        description=f"""
        Based on the candidate profile analysis below, recommend the top 3 most valuable community groups from the provided group listings.
        
        Candidate Analysis:
        ```
        {json.dumps(candidate_analysis, indent=2)}
        ```
        
        Available Groups:
        ```
        {json.dumps(groups_data, indent=2)}
        ```
        
        For each recommendation, explain why this community group would be particularly valuable for the candidate's professional growth.
        Consider factors such as group focus, networking opportunities, peer learning potential, and alignment with career interests.
        
        Provide your recommendations in a JSON format with a 'recommendations' array containing objects with:
        1. group_name
        2. member_count
        3. group_url (extract from the data if available)
        4. match_score (1-100)
        5. match_explanation (detailed reasoning)
        6. networking_value (specific networking benefits)
        """,
        agent=community_recommender_agent,
        expected_output="A JSON with top 3 community group recommendations with networking value explanations and URLs"
    )

def parse_json_result(crew_output):
    """Helper function to parse JSON from CrewAI output"""
    try:
        # Convert CrewOutput to string
        output_str = str(crew_output)
        
        # Try to extract JSON from code blocks first
        import re
        json_match = re.search(r'```(?:json)?\n(.*?)\n```', output_str, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # If no code block, try parsing the whole string
        return json.loads(output_str)
    except json.JSONDecodeError:
        # If all else fails, return the raw text
        return {"raw_result": output_str}
# Separate recommendation functions for HerKey.com data

def get_job_recommendations(candidate_profile):
    """Function to get only job recommendations for a candidate"""
    # Load only job data
    print("Loading job data...")
    job_data = load_data('jobs')
    
    # Create required agents
    print("Creating profile analyzer and job recommender agents...")
    profile_analyzer = create_profile_analyzer_agent()
    job_recommender = create_job_recommender_agent()
    
    # Step 1: Analyze candidate profile
    profile_analysis_task = create_profile_analysis_task(profile_analyzer, candidate_profile)
    profile_crew = Crew(
        agents=[profile_analyzer],
        tasks=[profile_analysis_task],
        verbose=True,
        process=Process.sequential
    )
    profile_analysis_result = profile_crew.kickoff()
    
    # Parse profile analysis
    try:
        profile_analysis_str = str(profile_analysis_result)
        import re
        json_match = re.search(r'```(?:json)?\n(.*?)\n```', profile_analysis_str, re.DOTALL)
        if json_match:
            profile_analysis = json.loads(json_match.group(1))
        else:
            profile_analysis = json.loads(profile_analysis_str)
    except json.JSONDecodeError:
        print("Warning: Could not parse profile analysis as JSON. Using raw text.")
        profile_analysis = {"raw_result": profile_analysis_str}
    
    # Step 2: Generate job recommendations
    print("Generating job recommendations...")
    job_task = create_job_recommendation_task(job_recommender, profile_analysis, job_data['jobs'])
    job_crew = Crew(
        agents=[job_recommender],
        tasks=[job_task],
        verbose=True,
        process=Process.sequential
    )
    job_result = job_crew.kickoff()
    job_recommendations = parse_json_result(job_result)
    
    return job_recommendations.get("recommendations", [])

def get_event_recommendations(candidate_profile):
    """Function to get only event recommendations for a candidate"""
    # Load only event data
    print("Loading event data...")
    event_data = load_data('events')
    
    # Create required agents
    print("Creating profile analyzer and event recommender agents...")
    profile_analyzer = create_profile_analyzer_agent()
    event_recommender = create_event_recommender_agent()
    
    # Step 1: Analyze candidate profile
    profile_analysis_task = create_profile_analysis_task(profile_analyzer, candidate_profile)
    profile_crew = Crew(
        agents=[profile_analyzer],
        tasks=[profile_analysis_task],
        verbose=True,
        process=Process.sequential
    )
    profile_analysis_result = profile_crew.kickoff()
    
    # Parse profile analysis
    try:
        profile_analysis_str = str(profile_analysis_result)
        import re
        json_match = re.search(r'```(?:json)?\n(.*?)\n```', profile_analysis_str, re.DOTALL)
        if json_match:
            profile_analysis = json.loads(json_match.group(1))
        else:
            profile_analysis = json.loads(profile_analysis_str)
    except json.JSONDecodeError:
        print("Warning: Could not parse profile analysis as JSON. Using raw text.")
        profile_analysis = {"raw_result": profile_analysis_str}
    
    # Step 2: Generate event recommendations
    print("Generating event recommendations...")
    event_task = create_event_recommendation_task(event_recommender, profile_analysis, event_data['events'])
    event_crew = Crew(
        agents=[event_recommender],
        tasks=[event_task],
        verbose=True,
        process=Process.sequential
    )
    event_result = event_crew.kickoff()
    event_recommendations = parse_json_result(event_result)
    
    return event_recommendations.get("recommendations", [])

def get_session_recommendations(candidate_profile):
    """Function to get only session recommendations for a candidate"""
    # Load only session data
    print("Loading session data...")
    session_data = load_data('sessions')
    
    # Create required agents
    print("Creating profile analyzer and session recommender agents...")
    profile_analyzer = create_profile_analyzer_agent()
    session_recommender = create_session_recommender_agent()
    
    # Step 1: Analyze candidate profile
    profile_analysis_task = create_profile_analysis_task(profile_analyzer, candidate_profile)
    profile_crew = Crew(
        agents=[profile_analyzer],
        tasks=[profile_analysis_task],
        verbose=True,
        process=Process.sequential
    )
    profile_analysis_result = profile_crew.kickoff()
    
    # Parse profile analysis
    try:
        profile_analysis_str = str(profile_analysis_result)
        import re
        json_match = re.search(r'```(?:json)?\n(.*?)\n```', profile_analysis_str, re.DOTALL)
        if json_match:
            profile_analysis = json.loads(json_match.group(1))
        else:
            profile_analysis = json.loads(profile_analysis_str)
    except json.JSONDecodeError:
        print("Warning: Could not parse profile analysis as JSON. Using raw text.")
        profile_analysis = {"raw_result": profile_analysis_str}
    
    # Step 2: Generate session recommendations
    print("Generating session recommendations...")
    session_task = create_session_recommendation_task(session_recommender, profile_analysis, session_data['sessions'])
    session_crew = Crew(
        agents=[session_recommender],
        tasks=[session_task],
        verbose=True,
        process=Process.sequential
    )
    session_result = session_crew.kickoff()
    session_recommendations = parse_json_result(session_result)
    
    return session_recommendations.get("recommendations", [])

def get_community_recommendations(candidate_profile):
    """Function to get only community recommendations for a candidate"""
    # Load only community/groups data
    print("Loading community data...")
    group_data = load_data('groups')
    
    # Create required agents
    print("Creating profile analyzer and community recommender agents...")
    profile_analyzer = create_profile_analyzer_agent()
    community_recommender = create_community_recommender_agent()
    
    # Step 1: Analyze candidate profile
    profile_analysis_task = create_profile_analysis_task(profile_analyzer, candidate_profile)
    profile_crew = Crew(
        agents=[profile_analyzer],
        tasks=[profile_analysis_task],
        verbose=True,
        process=Process.sequential
    )
    profile_analysis_result = profile_crew.kickoff()
    
    # Parse profile analysis
    try:
        profile_analysis_str = str(profile_analysis_result)
        import re
        json_match = re.search(r'```(?:json)?\n(.*?)\n```', profile_analysis_str, re.DOTALL)
        if json_match:
            profile_analysis = json.loads(json_match.group(1))
        else:
            profile_analysis = json.loads(profile_analysis_str)
    except json.JSONDecodeError:
        print("Warning: Could not parse profile analysis as JSON. Using raw text.")
        profile_analysis = {"raw_result": profile_analysis_str}
    
    # Step 2: Generate community recommendations
    print("Generating community recommendations...")
    community_task = create_community_recommendation_task(community_recommender, profile_analysis, group_data['groups'])
    community_crew = Crew(
        agents=[community_recommender],
        tasks=[community_task],
        verbose=True,
        process=Process.sequential
    )
    community_result = community_crew.kickoff()
    community_recommendations = parse_json_result(community_result)
    
    return community_recommendations.get("recommendations", [])

# Modified example usage
if __name__ == "__main__":
    # Sample candidate profile from MongoDB
    candidate_profile = {
        "_id": {"$oid": "6809c3daa03a7a1e240ab91f"},
        "user_id": "6809c002a03a7a1e240ab91e",
        "education": "Bachelor's Degree",
        "skills": ["Python", "Java", "AI", "NLP", "ML", "DL", "wed development", "app deelopment"],
        "current_status": "Looking for Work",
        "experience_years": {"$numberInt": "1"},
        "last_job": {"title": "AI developer", "company": "OLVT"},
        "life_stage": {"pregnancy_status": "No", "needs_flexible_work": False, "situation": "None of the above"},
        "job_preferences": {
            "type": "Remote Work",
            "roles": ["Software"],
            "short_term_goal": "Upskill and crack good placement",
            "long_term_goal": "Yes, i want to be an enterpreneur"
        },
        "location": {"city": "Tirupati", "relocation": True, "work_mode": "Flexible"},
        "community": {"wants_mentorship": True, "mentorship_type": "Skill development", "join_events": True},
        "communication_preference": "Email",
        "consent": True,
        "created_at": {"$date": {"$numberLong": "1745470426051"}}
    }
    
    # Example of getting only job recommendations
    session_results = get_session_recommendations(candidate_profile)
    
    print(session_results )
    
    print("\n Session recommendation process complete! ")
    
    # Example of getting only event recommendations
    # event_results = get_event_recommendations(candidate_profile)
    # with open("event_recommendations.json", "w") as f:
    #     json.dump(event_results, f, indent=2)
    # print("\nEvent recommendation process complete! Results saved to event_recommendations.json")
    
    # Uncomment to run other individual recommendation functions
    # session_results = get_session_recommendations(candidate_profile)
    # community_results = get_community_recommendations(candidate_profile)
    # profile_analysis = get_profile_analysis_only(candidate_profile)