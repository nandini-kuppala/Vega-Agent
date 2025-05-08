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

# Add the project root directory to the Python path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
# Import pages
from user_profile.login import login_page
from user_profile.signup import signup_page
from user_profile.questionnaire import questionnaire_page

from utils.design_utils import inject_global_styles
from Screens.home import display_home_page
from Screens.profile import display_profile_modal
from Screens.chat_page import display_chat_page


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
    
    # Use session state for authentication persistence
    # Enhanced session persistence with browser local storage
    if 'authenticated' in st.session_state and st.session_state['authenticated']:
        # Store authentication in browser storage for persistence
        session_data = {
            'authenticated': True,
            'user_id': st.session_state.get('user_id', ''),
            'token': st.session_state.get('token', ''),
            'page': st.session_state.get('page', 'home')
        }
        # Use JSON to store complex data
        st.query_params(session=json.dumps(session_data))
    
    # Check for cached authentication on page load
    query_params = st.query_params()
    if 'session' in query_params and not st.session_state.get('authenticated'):
        try:
            session_data = json.loads(query_params['session'][0])
            if session_data.get('authenticated'):
                st.session_state['authenticated'] = True
                st.session_state['user_id'] = session_data.get('user_id', '')
                st.session_state['token'] = session_data.get('token', '')
                st.session_state['page'] = session_data.get('page', 'home')
        except:
            # If there's an error parsing the session data, don't restore the session
            pass

    # Apply custom CSS
    st.markdown("""
        <style>
            .sidebar-button {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                text-align: center;
                border-radius: 10px;
                margin: 10px 0;
                font-weight: bold;
                cursor: pointer;
                transition: 0.3s;
            }
            .sidebar-button:hover {
                background-color: #45a049;
            }
            .profile-icon-button {
                background: none;
                border: none;
                font-size: 26px;
                cursor: pointer;
            }
            /* Fix for audio recorder component */
            .stAudioRecorderWrapper {
                display: none !important;
            }
            .st-emotion-cache-1avcm0n {
                height: calc(100vh - 80px) !important;
                overflow-y: auto !important;
            }
        </style>
    """, unsafe_allow_html=True)

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
                st.rerun()

            if st.button("👤 Complete Profile", key="profile_btn", use_container_width=True):
                st.session_state['page'] = 'questionnaire'
                st.session_state['show_profile'] = False
                st.rerun()

            if st.button("🤖 Chat", key="chat_btn", use_container_width=True):
                st.session_state['page'] = 'chat'
                st.session_state['show_profile'] = False
                st.rerun()

            if st.button("🧠 Daily Knowledge Dose", key="knowledge_btn", use_container_width=True):
                st.session_state['page'] = 'knowledge_dose'
                st.session_state['show_profile'] = False
                st.rerun()

            if st.button("🚀 Your Roadmap", key="roadmap_btn", use_container_width=True):
                st.session_state['page'] = 'roadmap'
                st.session_state['show_profile'] = False
                st.rerun()
            
            if st.button("📝 Resume Builder", key="resume_btn", use_container_width=True):
                st.session_state['page'] = 'resume_builder'
                st.session_state['show_profile'] = False
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
                # Clear session storage to completely log out
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                # Clear session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
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
        st.error("Page not found!")
        st.session_state['page'] = 'login'
        st.rerun()


if __name__ == "__main__":
    main()
