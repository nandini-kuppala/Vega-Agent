import streamlit as st
import requests
import json
import os
from streamlit_lottie import st_lottie
from backend.database import signup_user
def load_lottie_file(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def signup_page():
    # Import styles
    from utils.design_utils import inject_global_styles, get_styles
    st.markdown(inject_global_styles(), unsafe_allow_html=True)
    styles = get_styles()
    
    st.markdown("<h1 class='highlight' style='text-align: center;'>Create Your Account</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Usage
        lottie_path = os.path.join("assets", "animations", "signup.json")  # Replace with your actual filename
        lottie_json = load_lottie_file(lottie_path)

        if lottie_json:
            st_lottie(lottie_json, height=300, key="signup")
    
    with col2:
        # Signup form
        name = st.text_input("Full Name", key="signup_name")
        email = st.text_input("Email", key="signup_email")
        phone = st.text_input("Phone Number", key="signup_phone")
        city = st.text_input("City", key="signup_city")
        password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm")
        
        signup_button = st.button("Sign Up", key="signup_button")
        if signup_button:
            if not name or not email or not phone or not city or not password or not confirm_password:
                st.error("Please fill in all fields")
            elif password != confirm_password:
                st.error("Passwords do not match")
            else:
                try:
                    # Direct MongoDB signup instead of API call
                    result = signup_user(email, password, name, phone, city)
                    
                    if result["status"] == "success":
                        # Store token and user_id in session state
                        st.session_state['token'] = result['access_token']
                        st.session_state['user_id'] = result['user_id']
                        st.session_state['authenticated'] = True
                        st.session_state['page'] = 'questionnaire'
                        st.success("Account created successfully! Let's build your profile.")
                        st.rerun()
                    else:
                        st.error(f"Error: {result['message']}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
    
    st.markdown("---")
    st.markdown("<p>Already have an account?</p>", unsafe_allow_html=True)
    
    if st.button("Login", key="goto_login"):
        st.session_state['page'] = 'login'
        st.rerun()