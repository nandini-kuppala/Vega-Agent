#career_guide.py

import os
import json
import re

from crewai import Agent, Task, Crew, Process
from utils.input import DateTimeEncoder
from Agentic_ai.herkey_rag import create_profile_analyzer_agent
from Agentic_ai.herkey_rag import create_profile_analysis_task
from Agentic_ai.herkey_rag import parse_json_result
from tavily import TavilyClient
from backend.database import get_profile
import google.generativeai as genai
from langchain_community.chat_models import ChatLiteLLM
import streamlit as st
from session_context.session_context_manager import (
    generate_consolidated_context, 
    generate_contextual_followups
)
from session_context.user_pattern_anlaysis import (
    enhanced_cross_session_analysis,
    get_user_pattern_summary,
    should_analyze_cross_session_patterns
)
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


# Initialize Tavily client
tavily_client = TavilyClient("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")

def get_user_preferences_summary(profile_data):
    """
    Extract and summarize user preferences from profile for query personalization
    """
    if not profile_data or profile_data.get('status') != 'success':
        return {}
    
    profile = profile_data.get('profile', {})
    
    preferences = {
        'skills': profile.get('skills', []),
        'experience_years': profile.get('experience_years', 0),
        'job_type': profile.get('job_preferences', {}).get('type', ''),
        'preferred_roles': profile.get('job_preferences', {}).get('roles', []),
        'location': profile.get('location', {}).get('city', ''),
        'work_mode': profile.get('location', {}).get('work_mode', ''),
        'relocation': profile.get('location', {}).get('relocation', False),
        'current_status': profile.get('current_status', ''),
        'education': profile.get('education', ''),
        'last_job': profile.get('last_job', {}),
        'short_term_goal': profile.get('job_preferences', {}).get('short_term_goal', ''),
        'long_term_goal': profile.get('job_preferences', {}).get('long_term_goal', '')
    }
    
    return preferences

def personalize_tavily_query(user_query, preferences):
    """
    Personalize the Tavily search query based on user profile and preferences
    """
    base_query = user_query.lower()
    
    # Add skills context if not already specified
    if preferences.get('skills') and not any(skill.lower() in base_query for skill in preferences['skills']):
        relevant_skills = preferences['skills'][:3]  # Top 3 skills
        skills_text = " ".join(relevant_skills)
        base_query = f"{base_query} {skills_text}"
    
    # Add experience level context
    exp_years = preferences.get('experience_years', 0)
    if exp_years == 0:
        experience_level = "fresher entry level"
    elif exp_years <= 2:
        experience_level = "junior"
    elif exp_years <= 5:
        experience_level = "mid level"
    else:
        experience_level = "senior"
    
    
    # Add location context if not specified
    location = preferences.get('location', '')
    if location and not any(city in base_query for city in ['bangalore', 'mumbai', 'delhi', 'hyderabad', 'pune', 'chennai']):
        if not preferences.get('relocation', False):
            base_query += f" in {location}"
    
    # Add salary expectations for job searches
    if any(keyword in base_query for keyword in ['job', 'position', 'role', 'hiring']):
        if exp_years >= 3:
            base_query += " salary above 15 LPA"
        elif exp_years >= 1:
            base_query += " salary above 8 LPA"
    
    return base_query.strip()

def get_tavily_search_results(query, search_type="general"):
    """
    Get search results from Tavily with error handling
    """
    try:
        if search_type == "jobs":
            # For job searches, include specific parameters
            response = tavily_client.search(
                query=query,
                search_depth="advanced",
                max_results=8
            )
        else:
            # For general searches (courses, resources, communities)
            response = tavily_client.search(
                query=query,
                search_depth="basic",
                max_results=6
            )
        
        return response
    except Exception as e:
        print(f"Error in Tavily search: {e}")
        return None

def format_tavily_results(tavily_response, query_type="general"):
    """
    Format Tavily search results for better presentation
    """
    if not tavily_response or not tavily_response.get('results'):
        return "I couldn't find specific results at the moment. Please try refining your search."
    
    results = tavily_response['results']
    formatted_results = []
    
    for result in results:
        title = result.get('title', 'No title')
        url = result.get('url', '#')
        content = result.get('content', '')[:200] + "..." if result.get('content') else ''
        
        formatted_results.append({
            'title': title,
            'url': url,
            'content': content
        })
    
    return formatted_results

def get_resources_with_links(user_query):
    """
    Enhanced function to get resources using Tavily search
    """
    user_id = st.session_state.get('user_id')
    
    # Get user profile for personalization
    profile_data = get_profile(user_id) if user_id else None
    preferences = get_user_preferences_summary(profile_data)
    
    # Personalize the query
    personalized_query = personalize_tavily_query(user_query, preferences)
    
    # Determine search type
    search_type = "jobs" if any(keyword in user_query.lower() for keyword in ['job', 'hiring', 'position', 'vacancy']) else "general"
    
    # Get Tavily results
    tavily_response = get_tavily_search_results(personalized_query, search_type)
    
    if tavily_response:
        formatted_results = format_tavily_results(tavily_response, search_type)
        return {
            'search_results': formatted_results,
            'personalized_query': personalized_query,
            'original_query': user_query
        }
    
    return None

def get_career_guidance_task(profile_analysis, user_query):
    """
    Enhanced career guidance task with integrated Tavily search and session context
    """
    user_id = st.session_state.get('user_id')
    session_id = st.session_state.get('current_session_id')
    
    # Initialize default values
    context_data = {}
    follow_ups = []
    pattern_summary = None
    tavily_data = None
    
    try:
        # Get consolidated context from previous sessions
        print(f"🔍 Getting consolidated context for user {user_id}")
        context_data = generate_consolidated_context(
            user_id=user_id, 
            current_session_id=session_id,
            current_query=user_query,
            limit=3
        ) or {}
        
        # Analyze user patterns
        print(f"🧠 Analyzing user patterns for user {user_id}")
        
        if should_analyze_cross_session_patterns(user_id):
            print("📊 Generating cross-session pattern analysis...")
            pattern_id = enhanced_cross_session_analysis(user_id, force_generate_missing=True)
            if pattern_id:
                print(f"✅ Cross-session analysis completed: {pattern_id}")
        
        pattern_summary = get_user_pattern_summary(user_id)
        
        # Generate contextual follow-ups
        print(f"💡 Generating contextual follow-ups for user {user_id}")
        follow_ups = generate_contextual_followups(
            user_id=user_id,
            current_query=user_query,
            consolidated_context=context_data
        ) or []
        
        # Get Tavily search results if applicable
        print(f"🔍 Checking if Tavily search is needed for query: {user_query}")
        category = "CAREER_GUIDANCE"  # Assuming this since we're in career guidance task
        
        print("🌐 Using Tavily search for enhanced results...")
        tavily_data = get_resources_with_links(user_query)
        if tavily_data:
            print(f"✅ Tavily search completed with {len(tavily_data.get('search_results', []))} results")
        
    except Exception as e:
        print(f"⚠️ Error in context/pattern analysis: {e}")
        context_data = {}
        follow_ups = []
        pattern_summary = None
        tavily_data = None
    
    # Build the enhanced task description with Tavily integration
    tavily_section = ""
    if tavily_data and tavily_data.get('search_results'):
        tavily_section = f"""
        **Live Search Results (From Web Search):**
        Based on your query "{user_query}", here are the most relevant and up-to-date results:
        
        {format_search_results_for_prompt(tavily_data['search_results'])}
        
        **Instructions for using search results:**
        - Prioritize information from these live search results based on query if the query doesn't require just give them as some useful resources for you
        - Include specific links and resources mentioned in the results
        - Format job listings with company names, roles, and application links
        - For courses/resources, include direct links and brief descriptions
        - For communities, provide joining instructions and links
        
        """
    
    task_description = f"""
        You are providing personalized career guidance with full context awareness and live web search results.

        **Current User Query:** {user_query}

        **Previous Session Context:**
        {context_data.get('context_summary', 'This appears to be a new user with no previous session history.')}

        **Key Context from Previous Sessions:**
        {', '.join(context_data.get('key_context_points', ['No previous context available']))}

        **User's Ongoing Interests:**
        {', '.join(context_data.get('ongoing_interests', ['To be determined from this session']))}

        **Previous Recommendations Given:**
        {', '.join(context_data.get('previous_recommendations', ['None']))}

        **User Learning & Interaction Patterns:**
        {format_pattern_summary(pattern_summary) if pattern_summary else 'Pattern analysis pending - adapt based on user responses in this session.'}
        
        **live search results:**
        {tavily_section}

        **Contextual Follow-up Suggestions:**
        {format_followups(follow_ups)}

        **Your Task:**
        1. Provide a comprehensive, personalized response to the user's current query
        2. 2. **RESOURCE INCLUSION RULES**:
           - **For job/course/tool queries**: Include relevant external links and resources from live search results (hyper links are mandarory)
           - **For advice queries**: Focus on guidance first, Present live search results as supplementary resources relating them with your main response          
        3. Include specific links, resources, and actionable information from the search results
        4. Reference relevant information from previous sessions naturally 
        5. Adapt your communication style based on the user's identified patterns:
           - If exploratory learner: Provide options and broader context
           - If systematic learner: Give structured, step-by-step guidance
           - If goal-oriented: Focus on actionable next steps
        6. For job searches: Include company names, role titles, salary ranges (if available), and direct application links
        7. For learning resources: Include course links, free/paid options, and learning roadmaps
        8. For communities: Provide joining links and steps to engage
        9. For resume help: Suggest specific tools with links and guidance
        10. End with a relevant follow-up question from Contextual Follow-up Suggestions
        11. Be conversational and avoid mentioning this is a "follow-up question" - make it feel natural
        12. Keep the response informative yet concise (aim for 250-350 words)
        13. Use emojis (6-8 emojis) and have nice formatting with headings, subheadings and points
        14. **Format all links as clickable hyperlinks in markdown format: [Link Text](URL)**

        **Important:** Your response should feel like a continuation of an ongoing conversation, naturally incorporating both live search results and past discussions while addressing the current query with specific, actionable information.
        """
    
    return Task(
        description=task_description,
        agent=general_purpose_agent(),
        expected_output="A personalized career guidance response that incorporates live search results, previous session context, adapts to user patterns, and includes specific links and actionable information with a contextual follow-up question."
    )

def format_search_results_for_prompt(search_results):
    """
    Format search results for inclusion in the prompt
    """
    if not search_results:
        return "No search results available."
    
    formatted = []
    for i, result in enumerate(search_results, 1):
        title = result.get('title', 'No title')
        url = result.get('url', '#')
        content = result.get('content', '')
        
        formatted.append(f"""
        {i}. **{title}**
           Link: {url}
           Description: {content}
        """)
    
    return "\n".join(formatted)




def format_pattern_summary(pattern_summary):
    """Format pattern summary for inclusion in task description"""
    if not pattern_summary:
        return "No established patterns yet."
    
    parts = []
    
    if pattern_summary.get('learning_style_pattern'):
        parts.append(f"Learning Style: {pattern_summary['learning_style_pattern']}")
    
    if pattern_summary.get('preferred_learning_depth'):
        parts.append(f"Learning Depth: {pattern_summary['preferred_learning_depth']}")
    
    if pattern_summary.get('consistent_interests'):
        interests = pattern_summary['consistent_interests'][:3]  # Limit to top 3
        parts.append(f"Key Interests: {', '.join(interests)}")
    
    if pattern_summary.get('recommended_approach'):
        parts.append(f"Recommended Approach: {pattern_summary['recommended_approach']}")
    
    return ' | '.join(parts) if parts else "Analysis in progress."

def format_followups(follow_ups):
    """Format follow-up suggestions for inclusion in task description"""
    if not follow_ups:
        return "Generate appropriate follow-up based on current conversation."
    
    formatted = []
    for i, followup in enumerate(follow_ups[:2], 1):  # Limit to 2 suggestions
        if isinstance(followup, dict):
            question = followup.get('question', followup.get('suggestion', ''))
            rationale = followup.get('rationale', '')
            if question:
                formatted.append(f"{i}. {question}")
                if rationale:
                    formatted.append(f"   Rationale: {rationale}")
        else:
            formatted.append(f"{i}. {followup}")
    
    return '\n'.join(formatted) if formatted else "Generate contextually appropriate follow-up."



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