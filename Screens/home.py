
import streamlit as st
from backend.database import get_profile

def display_home_page():
    """Display the home page after login"""
    
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        st.warning("Please sign in first")
        st.session_state['page'] = 'login'
        st.rerun()
        return
    
    st.title("Welcome to ASHA AI Assistant")
    
    if 'user_id' in st.session_state:
        user_id = st.session_state['user_id']
    else:
        print("Not logged in")
    # Try to get user profile information
    try:
        # Use direct database function instead of API call
        result = get_profile(st.session_state['user_id'])
        
        if result["status"] == "success":
            profile_data = result["profile"]
            # Display user information
            st.markdown(f"### Hello!! 👋👋👋 ")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Your Profile")
                st.write(f"🎓 Education: {profile_data.get('education', 'Not specified')}")
                st.write(f"💼 Experience: {profile_data.get('experience_years', 0)} years")
                st.write(f"🌆 Location: {profile_data.get('location', {}).get('city', 'Not specified')}")
                
                # Display skills as tags
                if profile_data.get('skills'):
                    st.write("🔧 Skills:")
                    skill_html = "<div style='display: flex; flex-wrap: wrap; gap: 8px;'>"
                    for skill in profile_data.get('skills', []):
                        skill_html += f"<span style='background-color: #f0f0f0; padding: 5px 10px; border-radius: 20px; font-size: 14px;'>{skill}</span>"
                    skill_html += "</div>"
                    st.markdown(skill_html, unsafe_allow_html=True)
            
            with col2:
                st.subheader("Next Steps")
                st.markdown("""
                📝 Complete your profile questionnaire if you haven't already
                
                💬 Start chatting with ASHA AI for personalized career guidance
                
                🔍 Explore job opportunities tailored to your profile
                """)
                
                # Call to action button
                if st.button("Complete Profile", key="home_complete_profile"):
                    st.session_state['page'] = 'questionnaire'
                    st.rerun()
        
        else:
            # Profile doesn't exist yet
            st.info("It looks like you haven't completed your profile questionnaire yet.")
            
            if st.button("Complete Your Profile Now"):
                st.session_state['page'] = 'questionnaire'
                st.rerun()
    
    except Exception as e:
        st.error(f"Error retrieving profile: {str(e)}")
        
        # Fallback content
        st.markdown("""
        ## Welcome to ASHA AI!
        
        We're excited to have you here. To get the most out of your experience,
        please complete your profile questionnaire.
        """)
        
        if st.button("Complete Your Profile"):
            st.session_state['page'] = 'questionnaire'
            st.rerun()

