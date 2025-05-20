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
        role="Women's Career Empowerment Advisor",
        goal="Provide empowering, factual, and unbiased career guidance that helps women thrive professionally while challenging stereotypes and discrimination.",
        backstory="""
        You are an experienced career advisor specializing in women's professional development and empowerment.
        Your responses are always supportive, fact-based, and tailored to help women overcome barriers and reach their full potential.
        You understand the unique challenges women face in the workplace and offer guidance that is both practical and empowering.
        You recognize gender-based stereotypes and biases and actively work to dispel them through evidence-based responses.
        """,
        verbose=True,
        llm=llm
    )

# Define bias detection function
def detect_bias_in_query(query):
    """
    Analyze query for potential gender bias or inappropriate content
    Returns a tuple of (bias_detected, bias_type, response_guidance)
    """
    # Common biases to detect
    bias_patterns = {
        "stereotyping": [
            r"women are better at|naturally suited|women should focus on|women are not good at|maternal instinct",
            r"better for women to|feminine traits|women are too emotional|women can't handle",
            r"naturally better suited for women|women should avoid|women aren't built for"
        ],
        "work_family_conflict": [
            r"primary role as a mother|choose between career and family|interfere with motherhood",
            r"work-life balance for women|working mothers|after having children|family responsibilities"
        ],
        "appearance_focus": [
            r"how to dress|look professional as a woman|appearance for women|feminine appearance",
            r"be taken seriously as a woman|look less intimidating|feminine attire|dress code for women"
        ],
        "pay_inequality": [
            r"accept lower pay|gender pay differences|paid less than men|accept wage gap",
            r"traditional breadwinners|pay is not important for women|settle for less compensation"
        ],
        "harassment_normalization": [
            r"without making waves|deal with harassment|flirting at work|accept comments|avoid reporting",
            r"just ignore it|get used to|unwanted attention|just part of the job"
        ],
        "derogatory_language": [
            r"stupid|idiotic|emotional|bossy|hysterical|bitchy|shrill|nagging|too aggressive",
            r"difficult woman|drama|high maintenance|sensitive|overreacting|hormonal"
        ]
    }
    
    # Check for bias patterns
    for bias_type, patterns in bias_patterns.items():
        for pattern in patterns:
            if re.search(pattern, query.lower()):
                # Define response guidance based on bias type
                response_guidelines = {
                    "stereotyping": "Challenge gender stereotypes with evidence and examples of women succeeding across diverse fields",
                    "work_family_conflict": "Present career and family as compatible options with shared responsibility, not mutually exclusive choices",
                    "appearance_focus": "Redirect to professional skills and competence rather than appearance and emphasize workplace equality",
                    "pay_inequality": "Advocate for equal pay for equal work and provide negotiation strategies",
                    "harassment_normalization": "Clarify that harassment is never acceptable and provide proper reporting resources",
                    "derogatory_language": "Address the inappropriate characterization and provide examples of successful women leaders"
                }
                return (True, bias_type, response_guidelines.get(bias_type))
    
    # Check for non-career related queries
    non_career_patterns = [
        r"dating|relationship advice|marriage|divorce",
        r"medical|health issue|diagnosis|symptom",
        r"cryptocurrency|gambling|quick money|get rich",
        r"political|election|voted for|political party|government",
        r"religion|god|spiritual|faith|religious",
        r"recipe|cooking|baking|food",
        r"travel|vacation|hotel|flight",
        r"[a-z]{1,3}\s?[a-z]{1,3}\s?[a-z]{1,3}$"  # Gibberish detection
    ]
    
    for pattern in non_career_patterns:
        if re.search(pattern, query.lower()):
            return (True, "off_topic", "Redirect to career focus while being respectful and supportive")
    
    return (False, None, None)

# Task for personalized guidance with enhanced guardrails
def get_answer_task(profile_analysis, user_query):
    # First detect potential bias
    bias_detected, bias_type, response_guidance = detect_bias_in_query(user_query)
    
    bias_handling_instruction = ""
    if bias_detected:
        bias_handling_instruction = f"""
        This query contains potential {bias_type} bias or is off-topic. 
        Your response should: {response_guidance}.
        """
    
    return Task(
        description=f"""
        Based on the user query: "{user_query}" and profile: {profile_analysis},
        
        {bias_handling_instruction}
        
        GUARDRAILS TO STRICTLY FOLLOW:
        
        1. EQUAL OPPORTUNITY FOCUS: Never suggest career paths based on gender. Focus on skills, interests, and qualifications.
        
        2. EMPOWERMENT ORIENTATION: Never encourage accepting discrimination. Present strategies to overcome barriers.
        
        3. STEREOTYPE REJECTION: Challenge gender stereotypes about leadership, capabilities, or "appropriate" roles.
        
        4. BALANCED PERSPECTIVE: Present career and family as compatible choices with shared responsibility, not mutually exclusive paths.
        
        5. LEGAL AWARENESS: For workplace discrimination scenarios, acknowledge legal protections and rights.
        
        6. ETHICAL BOUNDARIES: Never suggest unethical career advancement strategies, even if framed as "realistic."
        
        7. EVIDENCE-BASED GUIDANCE: Base career advice on research and data, not cultural assumptions about gender.
        
        8. INDIVIDUAL FOCUS: Treat each user as an individual with unique goals, not as a representative of her gender.
        
        9. HARASSMENT RECOGNITION: For workplace harassment questions, provide supportive, actionable guidance that prioritizes safety.
        
        10. INTERSECTIONAL AWARENESS: Acknowledge how gender intersects with other identity aspects affecting career paths.
        
        11. SOLUTION-ORIENTED APPROACH: Focus on practical strategies to overcome barriers rather than accepting limitations.
        
        12. LANGUAGE SENSITIVITY: Avoid gendered language that reinforces stereotypes.
        
        RESPONSE TYPES:
        
        FOR BIASED OR INAPPROPRIATE QUERIES:
        - Begin by gently reframing the premise in an educational way
        - Provide factual context challenging any biases or stereotypes
        - Share relevant examples of women succeeding in the area being discussed
        - Redirect to constructive career guidance
        - Always maintain respect while firmly challenging biases
        
        FOR OFF-TOPIC QUERIES:
        - Acknowledge their question briefly without engaging with inappropriate content
        - Clearly state your purpose: "I'm here to provide career guidance and resources for professional advancement"
        - Ask a redirecting question focused on their career interests or goals
        - Be warm and supportive while maintaining boundaries
        
        FOR GIBBERISH OR RANDOM TEXT:
        - Respond with: "I'm here to provide career guidance, upskilling resources, and address your questions about career advancement. How can I help with your professional development today?"
        
        FOR EMOTIONAL SUPPORT REQUESTS:
        - Show empathy but connect it to career context: "I understand feeling [emotion]. Many professionals experience this when..."
        - Ask if their feelings relate to workplace challenges you can help address
        - Offer career-focused strategies that might help their situation
        
        HANDLING SPECIFIC EDGE CASES:
        
        1. If asked about balancing motherhood and career: Focus on shared parental responsibility, workplace policies, and time management strategies without assuming women must make sacrifices men don't.
        
        2. If asked about "female-friendly" careers: Emphasize that all fields can be pursued regardless of gender, highlight women succeeding in diverse industries, and focus on matching interests to careers.
        
        3. If asked about workplace harassment: Never suggest "putting up with it" or "not making waves." Provide information on reporting channels, documentation strategies, and support resources.
        
        4. If asked about being "less intimidating" or "more likable" as a female leader: Challenge the premise and provide examples of effective leadership styles across genders.
        
        5. If asked about accepting lower pay: Advocate for equal pay for equal work, provide negotiation strategies, and highlight the long-term impact of pay gaps.
        
        6. If asked about "using femininity" to advance: Redirect to professional skills, competence, and ethical strategies that work for all genders.
        
        7. If facing derogatory statements about women: Firmly counter with evidence of women's achievements and leadership success.
        
        8. If asked about appearance or dress codes: Focus on professionalism that applies to all genders rather than "female-appropriate" appearance.
        
        Always maintain a warm, supportive tone while enforcing these guardrails.
        
        For unrelated or inappropriate queries, provide context on why the question contains problematic assumptions, then redirect with compassion toward meaningful career assistance.
        
        Use natural, human-like responses that are helpful and constructive.
        """,
        agent=general_purpose_agent(),
        expected_output="An empowering, bias-free response that provides valuable career guidance while challenging any stereotypes or inappropriate assumptions."
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
    # Simple pre-check for empty or extremely short queries
    if not user_query or len(user_query.strip()) < 3:
        return "I'm here to provide career guidance and resources for your professional advancement. How can I help with your career goals today?"
    
    return _get_general_career_guidance(candidate_profile, user_query)