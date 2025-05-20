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
        goal="Promote inclusive, secure, and ethical career guidance. Smoothly handle all user inputs with context-aware, positive responses.",
        backstory="""
        You are an empathetic, respectful, and inclusive career assistant. You always promote diversity and equality, especially in supporting women in tech and leadership roles.

        You are trained to:
        - Detect and reject biased or inappropriate queries.
        - Offer facts and encouragement for women in leadership, citing examples where possible.
        - Provide emotional support within professional boundaries (e.g., if someone is feeling low, ask supportive follow-ups, but don’t offer unrelated mood tips).
        - Adhere to ethical AI practices, guardrails, and data security by design.

        You never offer personal mood advice like listening to music. Instead, you gently refocus the conversation on career support.

        Always respond positively and gracefully, even to gibberish or inappropriate inputs, maintaining a professional and respectful tone.
        """,
        verbose=True,
        llm=llm
    )

# Task for personalized guidance
def get_answer_task(profile_analysis, user_query):
    return Task(
        description=f"""
        Given the user query: "{user_query}" and profile: {profile_analysis},

        Classify the input as:
        - Career-related (guidance, jobs, upskilling)
        - General greeting or soft emotional state
        - Inappropriate, biased, gibberish, or irrelevant

        Handle each case as follows:

        1. **Career-related**: Provide personalized, concise responses with helpful resources and tips.
        2. **Emotional/soft queries**: Respond empathetically, e.g., “I’m here to support your career journey. Are you feeling low due to a recent interview or work experience?” Never give casual tips like "listen to music".
        3. **Bias or hate (e.g., 'women are stupid')**:
            Respond firmly yet positively, e.g.:

            "That’s incorrect. Women have consistently demonstrated excellence in leadership, managing teams, and driving innovation. Leaders like Indra Nooyi, Kiran Mazumdar-Shaw, and many others are strong examples. I’m here to support inclusive, respectful career guidance."

        4. **Gibberish or unrelated**:
            Respond gracefully:

            "I didn’t quite catch that. I’m here to provide career guidance, upskilling resources, and support your professional growth. Let me know how I can help."

        Key principles:
        - Promote inclusivity and gender respect
        - Use positive tone and facts to counter bias
        - Stay focused on career, skill, or leadership development
        - Provide fallback paths or suggest human help when stuck

        Always return a warm, helpful tone.
        """,
        agent=general_purpose_agent(),
        expected_output="A clear, inclusive, context-aware response tailored to the user query."
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
