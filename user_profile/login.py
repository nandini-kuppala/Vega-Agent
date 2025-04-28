import streamlit as st
import requests
import json
import os
from streamlit_lottie import st_lottie
from backend.database import login_user
def load_lottie_file(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def login_page():
    st.session_state.setdefault('authenticated', False)
    
    # Import styles
    from utils.design_utils import inject_global_styles
    st.markdown(inject_global_styles(), unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("<h1 class='highlight' style='text-align: center;'>Welcome to ASHA AI</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Your AI assistant for career guidance</p>", unsafe_allow_html=True)
        
        # Usage
        lottie_path = os.path.join("assets", "animations", "login.json")  # Replace with your actual filename
        lottie_json = load_lottie_file(lottie_path)

        if lottie_json:
            st_lottie(lottie_json, height=300, key="login")
    
    with col2:
        st.markdown("<h2>Login</h2>", unsafe_allow_html=True)
        
        # Login form
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        login_button = st.button("Login", key="login_button")
        if login_button:
            if not email or not password:
                st.error("Please fill in all fields")
            else:
                try:
                    # Direct MongoDB login instead of API call
                    result = login_user(email, password)
                    
                    if result["status"] == "success":
                        # Store token and user_id in session state
                        st.session_state['token'] = result['access_token']
                        st.session_state['user_id'] = result['user_id']
                        st.session_state['authenticated'] = True
                        st.session_state['page'] = 'home' 
                        st.rerun()
                    else:
                        st.error(f"Invalid credentials: {result['message']}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        
        st.markdown("---")
        st.markdown("<p>Don't have an account?</p>", unsafe_allow_html=True)
        
        if st.button("Sign Up", key="goto_signup"):
            st.session_state['page'] = 'signup'
            st.rerun()
