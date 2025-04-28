import streamlit as st
import requests
import json
import os
from streamlit_lottie import st_lottie

def load_lottie_file(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def dashboard_page():
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        st.warning("Please sign in first")
        st.session_state['page'] = 'login'
        st.rerun()
        return
    
    # Import styles
    from utils.design_utils import inject_global_styles, get_styles
    st.markdown(inject_global_styles(), unsafe_allow_html=True)
    styles = get_styles()
    
    # Custom CSS for dashboard
    st.markdown("""
    <style>
    .dashboard-container {
        padding: 30px;
        margin: 20px 0;
        border-radius: 10px;
        background-color: #ffffff;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    
    .profile-card {
        border-left: 4px solid #935073;
        padding: 15px;
        margin: 10px 0;
        background-color: #f9f9f9;
        border-radius: 4px;
    }
    
    .stat-card {
        padding: 20px;
        border-radius: 8px;
        background-color: #f3f3f3;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        height: 100%;
    }
    
    .stat-value {
        font-size: 24px;
        font-weight: bold;
        color: #935073;
    }
    
    .stat-label {
        font-size: 14px;
        color: #666;
    }
    
    .chat-button {
        background-color: #bfee90;
        color: #333;
        border: none;
        border-radius: 20px;
        padding: 10px 20px;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s;
        text-align: center;
        display: block;
        width: 100%;
        margin-top: 20px;
    }
    
    .chat-button:hover {
        background-color: #a3d275;
        transform: translateY(-2px);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("<h1 class='highlight' style='text-align: center;'>Welcome to ASHA AI</h1>", unsafe_allow_html=True)
    
    # Attempt to load profile data
    try:
        user_id = st.session_state['user_id']
        response = requests.get(
            f"http://localhost:8000/api/profiles/{user_id}",
            headers={"Authorization": f"Bearer {st.session_state['token']}"}
        )
        
        if response.status_code == 200:
            profile_data = response.json()
            
            # Display profile overview
            st.markdown("<div class='dashboard-container'>", unsafe_allow_html=True)
            
            # User greeting with animation
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"<h2>Hello, {profile_data.get('name', 'there')}!</h2>", unsafe_allow_html=True)
                st.write("Your AI career assistant is ready to help.")
            
            with col2:
                # Load and display Lottie animation
                lottie_path = os.path.join("assets", "animations", "voice_ass.json")  # Replace with your actual filename
                lottie_json = load_lottie_file(lottie_path)

                if lottie_json:
                    st_lottie(lottie_json, height=300, key="voice_ass")
            
            # Stats overview
            st.markdown("<h3>Your Profile Stats</h3>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("<div class='stat-card'>", unsafe_allow_html=True)
                st.markdown("<div class='stat-value'>100%</div>", unsafe_allow_html=True)
                st.markdown("<div class='stat-label'>Profile Complete</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col2:
                st.markdown("<div class='stat-card'>", unsafe_allow_html=True)
                experience = profile_data.get('experience_years', 0)
                st.markdown(f"<div class='stat-value'>{experience}+</div>", unsafe_allow_html=True)
                st.markdown("<div class='stat-label'>Years Experience</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col3:
                st.markdown("<div class='stat-card'>", unsafe_allow_html=True)
                skills_count = len(profile_data.get('skills', []))
                st.markdown(f"<div class='stat-value'>{skills_count}</div>", unsafe_allow_html=True)
                st.markdown("<div class='stat-label'>Skills Listed</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Profile highlights
            st.markdown("<h3>Your Profile Highlights</h3>", unsafe_allow_html=True)
            
            st.markdown("<div class='profile-card'>", unsafe_allow_html=True)
            st.markdown("<strong>Career Status:</strong> " + profile_data.get('current_status', 'Not specified'), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='profile-card'>", unsafe_allow_html=True)
            st.markdown("<strong>Education:</strong> " + profile_data.get('education', 'Not specified'), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='profile-card'>", unsafe_allow_html=True)
            st.markdown("<strong>Skills:</strong> " + ", ".join(profile_data.get('skills', ['Not specified'])), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='profile-card'>", unsafe_allow_html=True)
            job_preferences = profile_data.get('job_preferences', {})
            st.markdown("<strong>Looking for:</strong> " + job_preferences.get('type', 'Not specified') + " roles in " + 
                       (", ".join(job_preferences.get('roles', ['Various fields'])) if job_preferences.get('roles') else 'Various fields'), 
                       unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Chat button
            if st.button("Chat with ASHA AI", key="chat_button", help="Start a conversation with ASHA AI"):
                st.session_state['page'] = 'chat'
                st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        else:
            st.error("Could not load profile. Please try again later.")
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
    
    # Logout option
    if st.button("Logout", key="logout_button"):
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state['page'] = 'login'
        st.rerun()