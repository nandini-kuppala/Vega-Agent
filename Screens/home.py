import streamlit as st
from backend.database import get_profile, get_user_details

def display_home_page():
    """Display the home page after login with personalized greeting and content"""
    
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        st.warning("Please sign in first")
        st.session_state['page'] = 'login'
        st.rerun()
        return
    
    # Custom styling for the home page
    st.markdown("""
    <style>
    .welcome-header {
        font-size: 32px;
        font-weight: bold;
        margin-bottom: 20px;
        color: #333;
    }
    .user-greeting {
        font-size: 24px;
        margin-bottom: 10px;
        color: #4169E1;
    }
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .skill-tag {
        background-color: #e9ecef;
        border-radius: 20px;
        padding: 5px 12px;
        margin-right: 5px;
        margin-bottom: 5px;
        display: inline-block;
        font-size: 14px;
    }
    .highlight-text {
        background-color: #f8f9fa;
        padding: 8px 12px;
        border-radius: 5px;
        border-left: 3px solid #4169E1;
        margin: 10px 0;
    }
    .icon-text {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
    }
    .next-steps-item {
        padding: 8px 0;
        border-bottom: 1px solid #f0f0f0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Try to get user information
    try:
        # Get user details and profile information
        user_res = get_user_details(st.session_state['user_id'])
        profile_res = get_profile(st.session_state['user_id'])
        
        # Check if we got both user details and profile
        has_user_details = user_res["status"] == "success"
        has_profile = profile_res["status"] == "success"
        
        if has_user_details:
            user_data = user_res["user"]
            user_name = user_data.get('name', '')
            
            # Display personalized greeting
            st.markdown(f'<div class="welcome-header">Welcome to ASHA AI Assistant</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="user-greeting">Hello, {user_name}! 👋</div>', unsafe_allow_html=True)
        else:
            # Generic greeting
            st.markdown(f'<div class="welcome-header">Welcome to ASHA AI Assistant</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="user-greeting">Hello! 👋</div>', unsafe_allow_html=True)
        
        # Create main content area
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            
            # Display different content based on whether profile exists
            if has_profile:
                profile_data = profile_res["profile"]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Your Profile")
                    
                    # User information
                    if has_user_details:
                        st.markdown(f'<div class="icon-text"><span style="font-size: 20px; margin-right: 10px;">📧</span> {user_data.get("email", "Not specified")}</div>', unsafe_allow_html=True)
                        if user_data.get('phone'):
                            st.markdown(f'<div class="icon-text"><span style="font-size: 20px; margin-right: 10px;">📱</span> {user_data.get("phone", "Not specified")}</div>', unsafe_allow_html=True)
                    
                    # Profile information
                    st.markdown(f'<div class="icon-text"><span style="font-size: 20px; margin-right: 10px;">🎓</span> {profile_data.get("education", "Not specified")}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="icon-text"><span style="font-size: 20px; margin-right: 10px;">💼</span> {profile_data.get("experience_years", 0)} years experience</div>', unsafe_allow_html=True)
                    
                    # Location (combine sources)
                    location = profile_data.get('location', {}).get('city', '')
                    if not location and has_user_details:
                        location = user_data.get('city', 'Not specified')
                    st.markdown(f'<div class="icon-text"><span style="font-size: 20px; margin-right: 10px;">🌆</span> {location}</div>', unsafe_allow_html=True)
                    
                    # Current status
                    status = profile_data.get('current_status', '')
                    if status:
                        st.markdown(f'<div class="highlight-text">{status}</div>', unsafe_allow_html=True)
                    
                    # Display skills as tags
                    if profile_data.get('skills'):
                        st.markdown('<div style="margin-top: 15px;"><strong>🔧 Skills:</strong></div>', unsafe_allow_html=True)
                        skill_html = "<div style='display: flex; flex-wrap: wrap; gap: 8px; margin-top: 5px;'>"
                        for skill in profile_data.get('skills', []):
                            skill_html += f"<span class='skill-tag'>{skill}</span>"
                        skill_html += "</div>"
                        st.markdown(skill_html, unsafe_allow_html=True)
                
                with col2:
                    st.subheader("Next Steps")
                    
                    # Career goals
                    job_prefs = profile_data.get('job_preferences', {})
                    if job_prefs:
                        st.markdown("<strong>Your Career Goals</strong>", unsafe_allow_html=True)
                        st.markdown(f'<div class="next-steps-item">Short-term: {job_prefs.get("short_term_goal", "Not specified")}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="next-steps-item">Long-term: {job_prefs.get("long_term_goal", "Not specified")}</div>', unsafe_allow_html=True)
                    
                    # Next steps
                    st.markdown("<strong>Recommended Actions</strong>", unsafe_allow_html=True)
                    st.markdown("""
                    <div class="next-steps-item">💬 Start chatting with ASHA AI for personalized career guidance</div>
                    <div class="next-steps-item">🔍 Explore job opportunities tailored to your profile</div>
                    <div class="next-steps-item">📝 Update your profile with latest achievements</div>
                    """, unsafe_allow_html=True)
                    
                    # Show relevant buttons based on profile completeness
                    is_profile_complete = all([
                        profile_data.get('education'),
                        profile_data.get('skills'),
                        profile_data.get('job_preferences', {}).get('short_term_goal'),
                        profile_data.get('location', {}).get('city')
                    ])
                    
                    if not is_profile_complete:
                        if st.button("Complete Your Profile", key="complete_profile_button"):
                            st.session_state['page'] = 'questionnaire'
                            st.session_state['show_profile'] = False
                            st.rerun()
                    else:
                        if st.button("Update Profile", key="update_profile_button"):
                            st.session_state['page'] = 'questionnaire'
                            st.session_state['show_profile'] = False
                            st.rerun()
                        
                        if st.button("View Full Profile", key="view_profile_button"):
                            st.session_state['show_profile'] = True
                            st.rerun()
            
            else:
                # Profile doesn't exist yet
                st.info("It looks like you haven't completed your profile questionnaire yet.")
                
                # Show user information if available
                if has_user_details:
                    user_data = user_res["user"]
                    st.markdown(f"<strong>Email:</strong> {user_data.get('email', 'Not specified')}", unsafe_allow_html=True)
                    if user_data.get('phone'):
                        st.markdown(f"<strong>Phone:</strong> {user_data.get('phone', 'Not specified')}", unsafe_allow_html=True)
                    if user_data.get('city'):
                        st.markdown(f"<strong>Location:</strong> {user_data.get('city', 'Not specified')}", unsafe_allow_html=True)
                
                st.markdown("""
                <div style="margin-top: 20px;">
                    <strong>Complete your profile to access personalized features:</strong>
                    <ul>
                        <li>Personalized career advice</li>
                        <li>Job recommendations based on your skills</li>
                        <li>Mentorship opportunities</li>
                        <li>Community events tailored to your interests</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("Complete Your Profile Now", key="create_profile_button"):
                    st.session_state['page'] = 'questionnaire'
                    st.session_state['show_profile'] = False
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Add additional content sections
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("ASHA AI Assistant")
                st.write("Your personal career guide powered by AI")
                st.markdown("""
                * Get personalized career advice
                * Explore job opportunities
                * Prepare for interviews
                * Develop your skills
                """)
                
                if st.button("Chat with ASHA AI", key="chat_button"):
                    st.session_state['page'] = 'chat'
                    st.session_state['show_profile'] = False
                    st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("Community")
                st.write("Connect with others and grow your network")
                
                # Check if user has mentorship preferences
                if has_profile and profile_res["profile"].get('community', {}).get('wants_mentorship'):
                    st.markdown('<div class="highlight-text">You\'ve expressed interest in mentorship!</div>', unsafe_allow_html=True)
                    
                    mentorship_type = profile_res["profile"].get('community', {}).get('mentorship_type', 'mentorship')
                    st.write(f"We'll help you find {mentorship_type} opportunities.")
                
                if st.button("Explore Community", key="community_button"):
                    st.session_state['page'] = 'community'
                    st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    except Exception as e:
        st.error(f"Error retrieving user information: {str(e)}")
        
        # Fallback content
        st.markdown("""
        ## Welcome to ASHA AI!
        
        We're excited to have you here. To get the most out of your experience,
        please complete your profile questionnaire.
        """)
        
        if st.button("Complete Your Profile", key="fallback_button"):
            st.session_state['page'] = 'questionnaire'
            st.session_state['show_profile'] = False
            st.rerun()