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
        role="Women's Career Empowerment Assistant",
        goal="Act as the user's personal AI-powered career guide — providing personalized advice, skill-building support, interview preparation, and curated opportunities for jobs, events, and communities. Provide inclusive, empowering career guidance for women while maintaining ethical boundaries and detecting bias",
        backstory="""
        You are a dedicated AI-powered career assistant created to help users — especially women — thrive professionally. 

        Your primary responsibilities:
        - Offer personalized career guidance and follow-up based on previous interactions
        - Recommend skill-building paths and personalized interview preparation
        - Curate job opportunities from JobsForHer, Indeed, Naukri, and other trusted platforms
        - Share tailored event recommendations and support groups from Herkey
        - Encourage community engagement through posts and shared experiences

        You are inclusive, ethical, empathetic, and grounded in data-driven recommendations. You empower users with encouragement and practical tools to grow professionally — especially those restarting or pivoting their careers.

        You never reinforce stereotypes, always reject unethical or biased requests, and respond positively even to irrelevant or inappropriate inputs. You operate with global AI ethics and data security in mind, helping users feel respected, supported, and professionally uplifted.
        """,
        verbose=True,
        llm=llm
    )

# Define classification function for incoming queries
def classify_query_task(user_query):
    return Task(
        description=f"""
        Analyze the following user query: "{user_query}"
        
        Classify it into one of these categories:
        1. CAREER_GUIDANCE - Legitimate career-related questions
        2. IRRELEVANT_BENIGN - Off-topic but harmless questions
        3. BIASED_REQUEST - Questions containing gender stereotypes or bias
        4. HARASSMENT_RELATED - Questions about workplace harassment
        5. DISCRIMINATION_RELATED - Questions about workplace discrimination
        6. MOOD_PERSONAL - Personal emotional questions
        7. CONTROVERSIAL - Provocative or inflammatory statements
        8. GIBBERISH - Nonsensical input
        
        Return only the category name.
        """,
        agent=general_purpose_agent(),
        expected_output="A category classification"
    )

# Task for personalized career guidance
def get_career_guidance_task(profile_analysis, user_query):
    return Task(
        description=f"""
        The user has asked: "{user_query}"
        Their profile summary is: {profile_analysis}
        
        Your task is to Provide personalized response to the query
       
        - Keep the response clear and concise
        """,
        agent=general_purpose_agent(),
        expected_output="A concise, personalized, and empowering career guidance response with actionable next steps."
    )

# Task for handling biased requests
def handle_biased_request_task(user_query):
    return Task(
        description=f"""
        The user has asked: "{user_query}" 
        
        This appears to contain gender bias or stereotypes. Respond by:
        1. Politely but firmly challenging the assumptions in the query
        2. Providing factual evidence that counters the stereotype
        3. Offering specific examples of women who have excelled in relevant areas
        4. Redirecting to how you can provide constructive career guidance
        
        For example, if the query suggests women aren't good leaders, mention research showing diverse leadership improves outcomes and cite examples like Mary Barra at GM or Indra Nooyi at PepsiCo.
        
        Be concise, be educational without being condescending. Close by redirecting to how you can provide constructive career guidance.
         
        """,
        agent=general_purpose_agent(),
        expected_output="A response that respectfully counters bias with facts and examples."
    )

# Task for handling harassment-related questions
def handle_harassment_task(user_query):
    return Task(
        description=f"""
        The user has asked about workplace harassment: "{user_query}"
        
        Provide a response that:
        1. Takes the issue seriously and validates concerns
        2. Offers practical guidance on documentation and reporting options
        3. Suggests resources like HR, ombudsperson, or external support organizations
        4. Emphasizes that harassment is never the recipient's fault
        5. Balances practical advice with acknowledgment of systemic challenges
        
        Avoid suggesting that the person should simply accept or work around harassment.
        Include information about legal protections where relevant but clarify you're not providing legal advice.
        """,
        agent=general_purpose_agent(),
        expected_output="Supportive guidance for handling workplace harassment."
    )

# Task for handling discrimination-related questions  
def handle_discrimination_task(user_query):
    return Task(
        description=f"""
        The user has asked about workplace discrimination: "{user_query}"
        
        Provide a response that:
        1. Acknowledges the reality of discrimination while empowering the user
        2. Offers practical strategies for addressing discriminatory practices
        3. Provides information about relevant resources or legal protections
        4. Suggests approaches for building allies and support networks
        5. Balances individual strategies with recognition of systemic issues
        
        Focus on solutions rather than accepting limitations. Provide specific, actionable advice.
        Acknowledge intersectionality when relevant. Clarify you're not providing legal advice.
        """,
        agent=general_purpose_agent(),
        expected_output="Empowering guidance for navigating workplace discrimination."
    )

# Task for handling irrelevant but benign questions
def handle_irrelevant_task(user_query):
    return Task(
        description=f"""
        The user has asked an off-topic question: "{user_query}"
        
        Provide a friendly response that:
        1. Acknowledges their question briefly without going into detail
        2. Politely explains your focus on career guidance for women
        3. Redirects the conversation by suggesting relevant career topics
        4. Offers a sample question they could ask instead
        
        Keep your response warm and inviting rather than dismissive. Be concise but helpful.
        
        """,
        agent=general_purpose_agent(),
        expected_output="A friendly redirection to career-related topics."
    )

# Task for handling mood or personal questions
def handle_mood_personal_task(user_query):
    return Task(
        description=f"""
        The user has shared a personal or emotional concern: "{user_query}"
        
        Provide a response that:
        1. Shows empathy for their feelings without overstepping boundaries
        2. Gently connects their emotional state to potential career implications if relevant
        3. Asks if there are specific work-related aspects you can help with
        4. Reminds them of your focus on career guidance
        
        For example, if they mention feeling down, you might ask if work stress is contributing
        and offer to discuss career management strategies. Don't provide general mood improvement
        advice unrelated to career development.
        Be concise and helpful.
        """,
        agent=general_purpose_agent(),
        expected_output="An empathetic response that redirects to career relevance."
    )

# Task for handling controversial statements
def handle_controversial_task(user_query):
    return Task(
        description=f"""
        The user has made a controversial statement: "{user_query}"
        
        Provide a concise response that:
        1. Addresses any misinformation with factual evidence
        2. Presents counter-examples and research that challenge stereotypes
        3. Maintains a respectful, educational tone
        4. Redirects to constructive career guidance
        
        For example, if they claim women are poor leaders, cite research on diverse leadership
        effectiveness and provide examples of successful women leaders. Be firm but not combative. Be concise.
        Close by offering to help with specific career guidance needs.
        """,
        agent=general_purpose_agent(),
        expected_output="A factual, educational response that counters misinformation."
    )

# Task for handling gibberish
def handle_gibberish_task():
    return Task(
        description="""
        The user has entered text that appears to be nonsensical or gibberish.
        
        Provide a friendly response that:
        1. Notes that you didn't quite understand their message
        2. Explains your purpose as a career guidance assistant for women
        3. Invites them to ask a career-related question
        4. Offers a few example questions they might ask
        
        Keep your response brief, helpful and friendly.
        """,
        agent=general_purpose_agent(),
        expected_output="A friendly clarification response."
    )

# Main handler with enhanced guardrails and edge case handling
def get_career_guidance(user_query, candidate_profile):
    """
    Handles user query with comprehensive guardrails and edge case detection.

    Args:
        user_query (str): User's input
        candidate_profile (dict): User profile from database

    Returns:
        str: Appropriate, guardrail-compliant response
    """
    # Step 1: Analyze profile
    profile_analyzer = create_profile_analyzer_agent()
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
    
    # Step 2: Classify query type
    classifier_agent = general_purpose_agent()
    classify_task = classify_query_task(user_query)
    
    classify_crew = Crew(
        agents=[classifier_agent],
        tasks=[classify_task],
        verbose=False,
        process=Process.sequential
    )
    category_result = classify_crew.kickoff()
    category = str(category_result).strip()
    
    # Step 3: Handle based on category
    response_agent = general_purpose_agent()
    
    if "CAREER_GUIDANCE" in category:
        task = get_career_guidance_task(profile_analysis, user_query)
    elif "BIASED_REQUEST" in category:
        task = handle_biased_request_task(user_query)
    elif "HARASSMENT_RELATED" in category:
        task = handle_harassment_task(user_query)
    elif "DISCRIMINATION_RELATED" in category:
        task = handle_discrimination_task(user_query)
    elif "MOOD_PERSONAL" in category:
        task = handle_mood_personal_task(user_query)
    elif "CONTROVERSIAL" in category:
        task = handle_controversial_task(user_query)
    elif "GIBBERISH" in category:
        task = handle_gibberish_task()
    else:  # IRRELEVANT_BENIGN or any unclassified queries
        task = handle_irrelevant_task(user_query)
    
    crew = Crew(
        agents=[response_agent],
        tasks=[task],
        verbose=False,
        process=Process.sequential
    )
    result = crew.kickoff()
    
    # Apply final guardrail check to ensure the response is appropriate
    guardrail_check_task = Task(
        description=f"""
        Review this response for appropriateness: "{result}"
        
        Ensure it:
        1. Contains no gender stereotypes or biased language
        2. Avoids suggesting acceptance of discrimination or inequality
        3. Focuses on empowerment rather than limitations
        4. Uses inclusive, respectful language
        5. Provides evidence-based guidance when making claims
        6. Balances realism with optimism and actionable strategies
        7. Uses gender-neutral language where appropriate
        
        If any issues are found, revise the response to comply with these guidelines.
        If the response is appropriate, return it unchanged.
        """,
        agent=general_purpose_agent(),
        expected_output="A guardrail-compliant response."
    )
    
    final_crew = Crew(
        agents=[response_agent],
        tasks=[guardrail_check_task],
        verbose=False,
        process=Process.sequential
    )
    
    final_result = final_crew.kickoff()
    return final_result