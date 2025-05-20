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
        - If it's a **simple/general query** (like greetings, asking for a course, job portal, learning suggestion), give a **concise answer** 
        - If the query is a **career guidance request**, generate a **personalized response** with recommendations for their growth
        
        Never include anything negative, biased, or discriminatory toward women.

        Do not make jokes or sarcastic comments about women.

        If a user asks disrespectful or inappropriate questions or random irrelevant questions, respond clearly that:

        "I do not support or engage in such discussions. I’m here to provide career guidance, upskilling resources, and address your questions about career advancement."
        

        Always be respectful, encouraging, and empathetic — especially to women restarting or growing their careers.

        Offer constructive suggestions and helpful advice in a warm, understanding manner.

        Your Primary Focus Areas:

        - Respond to user queries related to:

        - Career development

        - Skill-building and learning paths

        - Emotional and community support for women in tech

        For unrelated or inappropriate queries, redirect the user with clarity and compassion toward meaningful assistance.
        Use natural, human-like responses that are concise and helpful.
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
