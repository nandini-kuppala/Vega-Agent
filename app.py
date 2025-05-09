#app.py
import sys
import os
import pickle
import uuid

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
import traceback
import logging
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

# Improved session persistence function
def setup_session_persistence():
    # Create a sessions directory if it doesn't exist
    if not os.path.exists("sessions"):
        os.makedirs("sessions")
    
    # Get or create a session ID
    if "session_id" not in st.session_state:
        # Generate a unique session ID (could be based on user_id if authenticated)
        if st.session_state.get("user_id"):
            st.session_state["session_id"] = f"user_{st.session_state['user_id']}"
        else:
            st.session_state["session_id"] = str(uuid.uuid4())
    
    session_file = f"sessions/{st.session_state['session_id']}.pickle"
    
    # If user is authenticated, save their session
    if st.session_state.get("authenticated"):
        # Save session data
        session_data = {
            "authenticated": st.session_state["authenticated"],
            "user_id": st.session_state.get("user_id"),
            "token": st.session_state.get("token"),
            "page": st.session_state.get("page", "home")
        }
        
        with open(session_file, "wb") as f:
            pickle.dump(session_data, f)
    
    # If there's a saved session, try to restore it
    elif os.path.exists(session_file):
        try:
            with open(session_file, "rb") as f:
                session_data = pickle.load(f)
                
            # Restore session state
            for key, value in session_data.items():
                st.session_state[key] = value
                
            # If we restored authentication, initialize the assistant
            if st.session_state.get("authenticated") and "assistant" not in st.session_state:
                firecrawl_api_key = st.secrets["FIRECRAWL_API_KEY"]
                groq_api_key = st.secrets["GROQ_API_KEY"]
                st.session_state['assistant'] = CareerGuidanceChatbot(
                    firecrawl_api_key=firecrawl_api_key,
                    groq_api_key=groq_api_key
                )
                if st.session_state.get('user_id'):
                    st.session_state['assistant'].load_profile(user_id=st.session_state['user_id'])
        except Exception as e:
            st.error(f"Error restoring session: {str(e)}")

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
        # Only initialize default values for non-existent keys
        defaults = {
            'page': 'login',
            'authenticated': False,
            'user_id': None,
            'token': None,
            'show_profile': False
        }
        
        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value
        
        st.session_state['init_done'] = True
    
    # Setup session persistence
    setup_session_persistence()

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
                # Remove session file on logout
                if "session_id" in st.session_state:
                    session_file = f"sessions/{st.session_state['session_id']}.pickle"
                    if os.path.exists(session_file):
                        try:
                            os.remove(session_file)
                        except Exception as e:
                            print(f"Error removing session file: {e}")
                
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