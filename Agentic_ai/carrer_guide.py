import os
import json

from crewai import Agent, Task, Crew, Process
from utils.input import DateTimeEncoder
from Agentic_ai.herkey_rag import create_profile_analyzer_agent
from Agentic_ai.herkey_rag import create_profile_analysis_task
from Agentic_ai.herkey_rag import parse_json_result

import google.generativeai as genai

from langchain_community.chat_models import ChatLiteLLM
import streamlit as st

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

def general_purpose_agent():
    llm = ChatLiteLLM(
        model="gemini/gemini-2.0-flash-lite",
        api_key=GEMINI_API_KEY,
        temperature=0.2
    )
    
    return Agent(
        role="Women's Career Guidance Specialist",
        goal="Provide personalized, empathetic career guidance to women at various stages of their careers",
        backstory="""You are an expert career advisor with deep understanding of challenges and 
        opportunities for women in the workplace. You specialize in supporting women who are 
        starting, restarting, or raising their careers with empathetic, practical advice. 
        You have extensive knowledge of career paths, skill development, and strategies for 
        women's professional advancement.""",
        verbose=True,
        llm=llm
    )

def get_answer_task(profile_analysis, user_query):
    # Determine if this is a simple conversation or a career-specific query
    is_simple_query = len(user_query.split()) < 5 or user_query.lower() in [
        "hi", "hello", "hey", "good morning", "good afternoon", "good evening", 
        "how are you", "what's up", "help", "who are you", "tell me about yourself"
    ]
    
    if is_simple_query:
        description = f"""
        Respond to this simple greeting or question: "{user_query}"
        
        Knowing this about the user: {profile_analysis}
        
        Guidelines:
        1. Keep your response brief and conversational (1-3 sentences maximum)
        2. Be warm and friendly but professional
        3. Don't use section headers, structured formats, or excessive emojis
        4. Respond directly to their query without providing unrequested career advice
        5. Use natural, conversational Indian English
        6. If they're greeting you, greet them back warmly and ask how you can help with their career journey
        """
    else:
        description = f"""
        Respond to this query: "{user_query}"
        
        Based on this user profile: {profile_analysis}
        
        Guidelines:
        1. Be concise and directly address their specific question
        2. Only provide information relevant to their query
        3. Personalize the response using relevant details from their profile
        4. Use a natural, conversational tone with minimal formatting
        5. Only use markdown for readability when necessary
        6. Include 1-2 emojis maximum if appropriate
        7. Focus on being helpful rather than comprehensive
        8. Don't structure your response with multiple headers unless absolutely necessary
        9. Keep your response focused and to the point
        10. Use humanized Indian English
        """
    
    return Task(
        description=description,
        agent=general_purpose_agent(),
        expected_output="A concise, personalized response that directly addresses the query"
    )

def _get_general_career_guidance(candidate_profile, user_query):
    
    # Create required agents
    print("Creating profile analyzer agent...")
    profile_analyzer = create_profile_analyzer_agent()
    
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
    
    # Step 2: Generate response
    print("Generating response...")
    response_agent = general_purpose_agent()
    task = get_answer_task(profile_analysis, user_query)  # Pass both profile and query
    
    crew = Crew(
        agents=[response_agent],
        tasks=[task],
        verbose=True,
        process=Process.sequential
    )
    result = crew.kickoff()
    return result

# Main function to handle user queries
def get_career_guidance(user_query, candidate_profile):
    """
    Process user query and provide personalized career guidance based on profile
    
    Args:
        user_query (str): The user's specific career question
        candidate_profile (dict): The user's profile data from MongoDB
    
    Returns:
        str: Personalized career guidance response
    """
    # Check if query is relevant to career guidance
    irrelevant_response = "Our services focus on career guidance, education, entrepreneurship, and skill development for women. Please feel free to ask related questions."
    
    irrelevant_keywords = [
        "clothes", "shoes", "fashion", "sale", "discount", "shopping mall", "online store", "buy", "shopping cart",
        "movies", "tv shows", "music", "concerts", "video games", "streaming services", "netflix", "youtube", "celebrities",
        "recipes", "cooking", "restaurants", "menu", "fast food", "coffee", "pizza", "snacks", "wine",
        "vacation", "hotel booking", "flight tickets", "travel packages", "tour guides", "sightseeing", "travel destinations", "tourism",
        "furniture", "home decor", "cleaning services", "appliances", "gardening", "real estate", "home improvement",
        "credit cards", "loan interest rates", "stocks", "bonds", "cryptocurrency", "insurance", "personal finance",
        "gym workouts", "weight loss", "yoga poses", "diet plans", "medical symptoms", "prescription drugs", "vitamins",
        "dating", "relationships", "marriage", "family advice", "friendships", "social media",
        "painting", "photography", "sports", "gardening", "knitting", "hiking", "crafting",
        "weather", "sports scores", "celebrity gossip", "political news", "local events"
    ]

    
    # Check if query contains any relevant keywords
    if any(keyword in user_query.lower() for keyword in irrelevant_keywords):
        return irrelevant_response
    
    # Augment profile analysis with specific user query
    enhanced_profile = candidate_profile.copy()
    enhanced_profile["current_query"] = user_query
    
    # Get personalized career guidance
    guidance_response = _get_general_career_guidance(enhanced_profile, user_query)
    
    return guidance_response

# Example usage with the provided sample profile
if __name__ == "__main__":
    # Parse the sample profile
    sample_profile = {
        "education": "Bachelor's Degree",
        "skills": ["Python", "Java", "AI", "NLP", "ML", "DL", "web development", "app development"],
        "current_status": "Looking for Work",
        "experience_years": 1,
        "last_job": {"title": "AI developer", "company": "OLVT"},
        "life_stage": {"pregnancy_status": "No", "needs_flexible_work": False, "situation": "None of the above"},
        "job_preferences": {
            "type": "Remote Work",
            "roles": ["Software"],
            "short_term_goal": "Upskill and crack good placement",
            "long_term_goal": "Yes, i want to be an entrepreneur"
        },
        "location": {"city": "Tirupati", "relocation": True, "work_mode": "Flexible"},
        "community": {"wants_mentorship": True, "mentorship_type": "Skill development", "join_events": True},
        "communication_preference": "Email"
    }
    
    # Example query
    user_query = "How to prepare DSA to crack tech interviews for Google SDE roles?"
     
    # Get career guidance
    response = get_career_guidance(user_query, sample_profile)
    print(response)