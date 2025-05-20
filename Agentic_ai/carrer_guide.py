import os
import json
import re

from crewai import Agent, Task, Crew, Process
from utils.input import DateTimeEncoder
from Agentic_ai.herkey_rag import create_profile_analyzer_agent
from Agentic_ai.herkey_rag import create_profile_analysis_task
from Agentic_ai.herkey_rag import parse_json_result

import google.generativeai as genai
from langchain_community.chat_models import ChatLiteLLM
import streamlit as st

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# General-purpose LLM setup
def general_purpose_agent():
    llm = ChatLiteLLM(
        model="gemini/gemini-2.0-flash-lite",
        api_key=GEMINI_API_KEY,
        temperature=0.2
    )
    
    return Agent(
        role="Versatile Career Assistant",
        goal="Give concise, helpful responses. Provide personalized advice only when asked clearly or required.",
        backstory="""
        You are a smart, concise career assistant. Respond with short, useful answers to general questions.
        Provide personalized career guidance *only* when the user's query is clearly about career development,
        leadership growth, or personalized help based on their profile.
        Keep greetings and common queries friendly and simple.
        """,
        verbose=True,
        llm=llm
    )

# Task for personalized guidance
def get_answer_task(profile_analysis, user_query):
    return Task(
        description=f"""
        Based on the user query: "{user_query}" and profile: {profile_analysis},
        
        Determine the type of query:
        - If it's a **simple/general query** (like greetings, asking for a course, job portal, learning suggestion), give a **concise answer** without overly structured formatting.
        - If the query is a **career guidance request**, generate a **personalized response**.

        Personalized responses should:
        1. Identify if the user is a Starter, Restarter, or Raiser
        2. Recommend relevant upskilling paths
        3. Address career gaps or challenges
        4. Suggest communities or platforms helpful for women in tech
        5. Be short, supportive, and human – no long sections or unnecessary headers.

        Keep the language natural, helpful, and not overly enthusiastic. Avoid markdown headers or emojis for general queries.
        """,
        agent=general_purpose_agent(),
        expected_output="A concise and helpful answer appropriate to the user query and context."
    )

# Profile analysis + response generation
def _get_general_career_guidance(candidate_profile, user_query):
    profile_analyzer = create_profile_analyzer_agent()
    
    # Step 1: Analyze profile
    profile_analysis_task = create_profile_analysis_task(profile_analyzer, candidate_profile)
    profile_crew = Crew(
        agents=[profile_analyzer],
        tasks=[profile_analysis_task],
        verbose=False,
        process=Process.sequential
    )
    profile_analysis_result = profile_crew.kickoff()

    try:
        profile_analysis_str = str(profile_analysis_result)
        json_match = re.search(r'```(?:json)?\n(.*?)\n```', profile_analysis_str, re.DOTALL)
        if json_match:
            profile_analysis = json.loads(json_match.group(1))
        else:
            profile_analysis = json.loads(profile_analysis_str)
    except json.JSONDecodeError:
        profile_analysis = {"raw_result": profile_analysis_str}

    # Step 2: Generate response
    response_agent = general_purpose_agent()
    task = get_answer_task(profile_analysis, user_query)
    
    crew = Crew(
        agents=[response_agent],
        tasks=[task],
        verbose=False,
        process=Process.sequential
    )
    result = crew.kickoff()
    return result

# Main handler
def get_career_guidance(user_query, candidate_profile):
    """
    Handles user query and returns an appropriate, concise or personalized response.

    Args:
        user_query (str): User's input
        candidate_profile (dict): User profile from database

    Returns:
        str: Appropriate chatbot response
    """
    return _get_general_career_guidance(candidate_profile, user_query)
