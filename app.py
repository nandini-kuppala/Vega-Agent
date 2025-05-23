#app.py
import sys
import os

# Try to import pysqlite3 only if it's installed
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except (ImportError, KeyError):
    pass
from Agentic_ai.chatbot import CareerGuidanceChatbot
import streamlit as st
import requests
import json
import sys
import os
import sys
import traceback
import logging
import json
from datetime import datetime
from Roadmap.roadmap_page import display_roadmap_page
from skill_assessment import skill
from Resume.resume_builder_page import display_resume_builder_page
from Knowledge.knowledge_dose_page import display_daily_knowledge_page
from backend.database import create_chat_session, get_user_chat_sessions, save_session_messages, get_chat_session


# Add the project root directory to the Python path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
# Import pages
from user_profile.login import login_page
from user_profile.signup import signup_page
from user_profile.questionnaire import questionnaire_page

from utils.design_utils import inject_global_styles
from Screens.home import display_home_page
from Screens.profile import display_profile_modal
from Screens.chat_page import display_chat_page, handle_session_analysis


from session_context.session_summarizer_agent import process_session_for_summary
from session_context.pattern_analyzer_agent import analyze_session_pattern
from session_context.user_pattern_manager import should_update_preferences, analyze_pattern_evolution, should_update_preferences
from session_context.session_context_manager import generate_consolidated_context

def main():
    # Configure page
    st.set_page_config(
        page_title="ASHA AI Bot",
        page_icon="👩‍💼",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Apply global CSS
    inject_global_styles()

    # Initialize session state variables if they don't exist
    if 'init_done' not in st.session_state:
        for var in ['page', 'authenticated', 'user_id', 'token', 'show_profile']:
            if var not in st.session_state:
                st.session_state[var] = False if var != 'page' else 'login'
        st.session_state['init_done'] = True
    
    # Check for authentication in URL parameters FIRST before other logic
    query_params = st.query_params
    if 'token' in query_params and 'user_id' in query_params:
        st.session_state['authenticated'] = True
        st.session_state['token'] = query_params['token']
        st.session_state['user_id'] = query_params['user_id']
        
        # Explicitly set page from URL param if it exists
        if 'page' in query_params:
            st.session_state['page'] = query_params['page']
        elif 'page' not in st.session_state:
            st.session_state['page'] = 'home'  # Default page
    
    # If not authenticated but trying to access protected page, redirect to login
    if not st.session_state.get('authenticated', False) and st.session_state.get('page', 'login') != 'login' and st.session_state.get('page', 'login') != 'signup':
        st.session_state['page'] = 'login'
        st.query_params.clear()  # Clear URL params
    
    # If authenticated, ensure the URL contains auth params for persistence
    if st.session_state.get('authenticated', False):
        params_to_set = {
            'token': st.session_state.get('token', ''),
            'user_id': st.session_state.get('user_id', ''),
            'page': st.session_state.get('page', 'home')
        }
        
        # Update URL parameters with current state
        st.query_params.update(params_to_set)
        # Session Management for Chat

    if st.session_state.get('authenticated') and st.session_state.get('user_id'):
        # Check if we have a session_id in URL params first
        query_params = st.query_params
        url_session_id = query_params.get('session_id')
        current_session_id = st.session_state.get('current_session_id')
        
        # If URL has different session_id than current, we're switching sessions
        if url_session_id and url_session_id != current_session_id:
            # Process previous session before switching
            if current_session_id and st.session_state.get('messages'):
                handle_session_analysis()
            
            # Switch to new session
            st.session_state['current_session_id'] = url_session_id
            
            # Load new session messages
            session_data = get_chat_session(url_session_id)
            if session_data["status"] == "success":
                st.session_state['messages'] = session_data["session"]["messages"]
            else:
                st.session_state['messages'] = [{
                    "role": "assistant", 
                    "content": "Hi! I'm ASHA, your career assistant powered by AI. How can I help you today?", 
                    "feedback": None
                }]
        
        # If no current session, create one
        elif not current_session_id:
            if url_session_id:
                # Use session from URL
                st.session_state['current_session_id'] = url_session_id
                session_data = get_chat_session(url_session_id)
                if session_data["status"] == "success":
                    st.session_state['messages'] = session_data["session"]["messages"]
            else:
                # Create new session
                result = create_chat_session(st.session_state['user_id'])
                if result["status"] == "success":
                    st.session_state['current_session_id'] = result["session_id"]
                    # Update URL with new session_id
                    current_params = dict(st.query_params)
                    current_params['session_id'] = result["session_id"]
                    st.query_params.update(current_params)
                    
        # Ensure session_id is always in URL
        if st.session_state.get('current_session_id'):
            current_params = dict(st.query_params)
            if current_params.get('session_id') != st.session_state['current_session_id']:
                current_params['session_id'] = st.session_state['current_session_id']
                st.query_params.update(current_params)

    # Assistant Initialization
    if st.session_state.get('authenticated') and 'assistant' not in st.session_state:
        try:
            firecrawl_api_key = st.secrets["FIRECRAWL_API_KEY"]
            groq_api_key = st.secrets["GROQ_API_KEY"]
            st.session_state['assistant'] = CareerGuidanceChatbot(
                firecrawl_api_key=firecrawl_api_key,
                groq_api_key=groq_api_key
            )
            if st.session_state.get('user_id'):
                st.session_state['assistant'].load_profile(user_id=st.session_state['user_id'])
        except Exception as e:
            st.error(f"Error initializing assistant: {str(e)}")
            print(traceback.format_exc())

    # Top Header
    if st.session_state.get('authenticated'):
        col1, col2 = st.columns([9, 1])
        with col2:
            if st.button("👤", key="profile_icon", help="View your profile"):
                st.session_state['show_profile'] = not st.session_state['show_profile']
                st.rerun()

        # Sidebar Menu
        with st.sidebar:
            st.title("🌟 ASHA AI Bot")
            st.markdown("---")

            if st.button("🏠 Home", key="home_btn", use_container_width=True):
                st.session_state['page'] = 'home'
                st.session_state['show_profile'] = False
                # Update page in query params
                current_params = dict(st.query_params)
                current_params['page'] = 'home'
                st.query_params.update(current_params)
                st.rerun()

            if st.button("👤 Complete Profile", key="profile_btn", use_container_width=True):
                st.session_state['page'] = 'questionnaire'
                st.session_state['show_profile'] = False
                # Update page in query params
                current_params = dict(st.query_params)
                current_params['page'] = 'questionnaire'
                st.query_params.update(current_params)
                st.rerun()

            if st.button("🤖 Chat", key="chat_btn", use_container_width=True):
                st.session_state['page'] = 'chat'
                st.session_state['show_profile'] = False
                # Update page in query params
                current_params = dict(st.query_params)
                current_params['page'] = 'chat'
                st.query_params.update(current_params)
                st.rerun()

            if st.button("🧠 Daily Knowledge Dose", key="knowledge_btn", use_container_width=True):
                st.session_state['page'] = 'knowledge_dose'
                st.session_state['show_profile'] = False
                # Update page in query params
                current_params = dict(st.query_params)
                current_params['page'] = 'knowledge_dose'
                st.query_params.update(current_params)
                st.rerun()

            if st.button("🚀 Your Roadmap", key="roadmap_btn", use_container_width=True):
                st.session_state['page'] = 'roadmap'
                st.session_state['show_profile'] = False
                # Update page in query params
                current_params = dict(st.query_params)
                current_params['page'] = 'roadmap'
                st.query_params.update(current_params)
                st.rerun()
            
            if st.button("📝 Resume Builder", key="resume_btn", use_container_width=True):
                st.session_state['page'] = 'resume_builder'
                st.session_state['show_profile'] = False
                # Update page in query params
                current_params = dict(st.query_params)
                current_params['page'] = 'resume_builder'
                st.query_params.update(current_params)
                st.rerun()

            st.markdown(
                """
                <a href="https://skillassessment.streamlit.app/" target="_blank">
                    <button style="
                        background-color:white;
                        color:black;
                        border:1px solid lightgray;
                        padding:0.6em;
                        margin-bottom:1em;
                        font-size:1em;
                        width:100%;
                        cursor:pointer;
                        border-radius:10px;
                        text-align:center;
                    ">
                        📋 Skill Assessment
                    </button>
                </a>
                """,
                unsafe_allow_html=True
            )

            st.markdown("---")
            if st.button("🚪 Logout", key="logout_btn", use_container_width=True):
                # Save current session before logout
                if st.session_state.get('current_session_id') and st.session_state.get('messages'):
                    try:
                        save_session_messages(st.session_state['current_session_id'], st.session_state['messages'])
                        handle_session_analysis()  # Process final session analysis
                    except Exception as e:
                        print(f"Error saving session on logout: {str(e)}")
                    
                # Clear session storage to completely log out
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                # Clear URL parameters
                st.query_params.clear()
                st.session_state['page'] = 'login'
                st.rerun()
            
            st.markdown("---")

            st.info("""
            **Why wait for quality?** ⏳💡
            
            ASHA's responses may take a moment as our advanced AI 🤖 carefully analyzes your profile to provide truly personalized recommendations tailored just for you 🧠.
            
            The longer you allow ASHA to think, the more accurate 🎯 and valuable 💎 your recommendations will be!
            """)


    # Show Profile Modal
    if st.session_state.get('show_profile') and st.session_state.get('authenticated'):
        display_profile_modal()

    # Page Routing
    page = st.session_state.get('page', 'login')

    # Debug information (optional - can be removed in production)
    # st.sidebar.write(f"Current page: {page}")
    # st.sidebar.write(f"URL params: {dict(st.query_params)}")

    if page == 'login':
        login_page()
    elif page == 'signup':
        signup_page()
    elif page == 'questionnaire':
        questionnaire_page()
    elif page == 'roadmap':
        display_roadmap_page()
    elif page == 'home':
        display_home_page()
    elif page == 'chat':
        display_chat_page()   
    elif page == 'resume_builder':
        display_resume_builder_page() 
    elif page == 'knowledge_dose':
        display_daily_knowledge_page()
    else:
        st.error(f"Page not found: {page}")
        st.session_state['page'] = 'home'
        st.query_params.update({'page': 'home'})
        st.rerun()


if __name__ == "__main__":
    main()