import streamlit as st
from backend.database import get_profile, get_user_details

def display_profile_modal():
    """Display user profile in a visually appealing modal."""
    
    # Create a container with custom styling for the modal
    st.markdown("""
    <style>
    .profile-modal {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .profile-header {
        display: flex;
        align-items: center;
        margin-bottom: 20px;
    }
    .profile-section {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
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
    .contact-info {
        margin-top: 5px;
        font-size: 14px;
        color: #6c757d;
    }
    </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="profile-modal">', unsafe_allow_html=True)
        
        st.markdown('<h2>Your Profile</h2>', unsafe_allow_html=True)
        
        close_profile = st.button("✕ Close", key="close_profile")
        if close_profile:
            st.session_state['show_profile'] = False
            st.rerun()
        
        # Check if user_id exists in session state
        if 'user_id' not in st.session_state:
            st.error("Please log in again.")
            st.markdown('</div>', unsafe_allow_html=True)
            return            
        
        # Get profile data
        try:
            profile_res = get_profile(st.session_state['user_id'])
            user_res = get_user_details(st.session_state['user_id'])
            
            if profile_res["status"] == "success" and user_res["status"] == "success":
                profile = profile_res["profile"]
                user = user_res["user"]
            else:
                error_message = profile_res.get("message", "") or user_res.get("message", "Failed to retrieve data.")
                st.error(error_message)
                st.markdown('</div>', unsafe_allow_html=True)
                return
        except Exception as e:
            st.error(f"Error retrieving profile: {str(e)}")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        
        # User header with avatar and basic user details
        st.markdown('<div class="profile-header">', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 64px; margin-right: 20px;">👤</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div>
            <h3 style="margin: 0;">{user.get('name', 'User')}</h3>
            <p style="margin: 0; font-size: 18px;">{profile.get('education', 'Education not specified')}</p>
            <p style="margin: 0; color: #6c757d;">Experience: {profile.get('experience_years', 0)} years</p>
            <p style="margin: 0; color: #6c757d;">{user.get('city', '') or profile.get('location', {}).get('city', 'Location not specified')}</p>
            <div class="contact-info">
                <p style="margin: 0;"><strong>Email:</strong> {user.get('email', 'Not specified')}</p>
                <p style="margin: 0;"><strong>Phone:</strong> {user.get('phone', 'Not specified')}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="profile-section">', unsafe_allow_html=True)
            st.subheader("Skills & Expertise")
            
            # Display skills as visual tags
            skills = profile.get('skills', [])
            if skills:
                tags_html = ""
                for skill in skills:
                    tags_html += f'<span class="skill-tag">{skill}</span>'
                st.markdown(tags_html, unsafe_allow_html=True)
            else:
                st.write("No skills specified yet")
            
            st.write(f"**Current Status:** {profile.get('current_status', 'Not specified')}")
            
            if profile.get('last_job'):
                st.write(f"**Last Position:** {profile['last_job'].get('title', 'Not specified')} at {profile['last_job'].get('company', 'Not specified')}")
            
            # Display life stage information if available
            life_stage = profile.get('life_stage', {})
            if any(life_stage.values()):
                st.subheader("Life Stage")
                if life_stage.get('situation') and life_stage.get('situation') != "None of the above":
                    st.write(f"**Situation:** {life_stage.get('situation')}")
                if life_stage.get('pregnancy_status') == "Yes":
                    st.write("**Pregnancy Status:** Yes")
                if life_stage.get('needs_flexible_work'):
                    st.write("**Needs Flexible Work:** Yes")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="profile-section">', unsafe_allow_html=True)
            st.subheader("Career Goals")
            
            job_prefs = profile.get('job_preferences', {})
            st.write(f"**Short-term Goal:** {job_prefs.get('short_term_goal', 'Not specified')}")
            st.write(f"**Long-term Goal:** {job_prefs.get('long_term_goal', 'Not specified')}")
            
            st.write("**Preferred Job Types:**")
            st.write(f"• {job_prefs.get('type', 'Not specified')}")
            
            roles = job_prefs.get('roles', [])
            if roles:
                st.write("**Interested Roles:**")
                for role in roles:
                    st.write(f"• {role}")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Work preferences section
        st.markdown('<div class="profile-section">', unsafe_allow_html=True)
        st.subheader("Work Preferences")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            location = profile.get('location', {})
            st.write(f"**Location:** {location.get('city', 'Not specified')}")
        with col2:
            st.write(f"**Work Mode:** {location.get('work_mode', 'Not specified')}")
        with col3:
            st.write(f"**Open to Relocation:** {'Yes' if location.get('relocation', False) else 'No'}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Community interests
        st.markdown('<div class="profile-section">', unsafe_allow_html=True)
        st.subheader("Community Engagement")
        
        community = profile.get('community', {})
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Wants Mentorship:** {'Yes' if community.get('wants_mentorship', False) else 'No'}")
            if community.get('wants_mentorship', False):
                st.write(f"**Mentorship Type:** {community.get('mentorship_type', 'Not specified')}")
        
        with col2:
            st.write(f"**Interested in Events:** {'Yes' if community.get('join_events', False) else 'No'}")
        
        if profile.get('communication_preference'):
            st.write(f"**Communication Preference:** {profile.get('communication_preference')}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Account information
        st.markdown('<div class="profile-section">', unsafe_allow_html=True)
        st.subheader("Account Information")
        
        st.write(f"**Member Since:** {user.get('created_at', 'Not available')}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Edit profile button
        if st.button("Edit Profile", key="edit_profile_modal"):
            st.session_state['page'] = 'questionnaire'
            st.session_state['show_profile'] = False
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

def display_profile():
    """Display user profile information."""
    st.title("Your Profile")
    
    # Check if user_id exists in session state
    if 'user_id' not in st.session_state:
        st.error("Please log in again.")
        return
        
    try:
        profile_res = get_profile(st.session_state['user_id'])
        user_res = get_user_details(st.session_state['user_id'])
        
        if profile_res["status"] == "success" and user_res["status"] == "success":
            profile = profile_res["profile"]
            user = user_res["user"]
        else:
            error_message = profile_res.get("message", "") or user_res.get("message", "Failed to retrieve data.")
            st.error(error_message)
            return
    except Exception as e:
        st.error(f"Error retrieving profile: {str(e)}")
        return
    
    # User header with basic details
    st.header(f"{user.get('name', 'User')}")
    st.write(f"**Email:** {user.get('email', 'Not specified')}")
    st.write(f"**Phone:** {user.get('phone', 'Not specified')}")
    st.write(f"**Member Since:** {user.get('created_at', 'Not available')}")
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Personal Information")
        st.write(f"**Education:** {profile.get('education', 'Not specified')}")
        st.write(f"**Experience:** {profile.get('experience_years', 0)} years")
        st.write(f"**Current Status:** {profile.get('current_status', 'Not specified')}")
        
        if profile.get('last_job'):
            st.write(f"**Last Job:** {profile['last_job'].get('title', 'Not specified')} at {profile['last_job'].get('company', 'Not specified')}")
        
        # Display life stage information if available
        life_stage = profile.get('life_stage', {})
        if any(life_stage.values()):
            st.subheader("Life Stage")
            if life_stage.get('situation') and life_stage.get('situation') != "None of the above":
                st.write(f"**Situation:** {life_stage.get('situation')}")
            if life_stage.get('pregnancy_status') == "Yes":
                st.write("**Pregnancy Status:** Yes")
            if life_stage.get('needs_flexible_work'):
                st.write("**Needs Flexible Work:** Yes")
        
        st.subheader("Skills")
        skills = profile.get('skills', [])
        if skills:
            for skill in skills:
                st.write(f"- {skill}")
        else:
            st.write("No skills specified")
    
    with col2:
        st.subheader("Preferences")
        
        job_prefs = profile.get('job_preferences', {})
        st.write(f"**Preferred Job Type:** {job_prefs.get('type', 'Not specified')}")
        
        roles = job_prefs.get('roles', [])
        if roles:
            st.write("**Preferred Roles:**")
            for role in roles:
                st.write(f"- {role}")
        
        st.write(f"**Short-term Goal:** {job_prefs.get('short_term_goal', 'Not specified')}")
        st.write(f"**Long-term Goal:** {job_prefs.get('long_term_goal', 'Not specified')}")
        
        location = profile.get('location', {})
        st.write(f"**Location:** {location.get('city', 'Not specified')}")
        st.write(f"**Work Mode:** {location.get('work_mode', 'Not specified')}")
        st.write(f"**Open to Relocation:** {'Yes' if location.get('relocation', False) else 'No'}")
        
        community = profile.get('community', {})
        st.write(f"**Wants Mentorship:** {'Yes' if community.get('wants_mentorship', False) else 'No'}")
        if community.get('wants_mentorship', False):
            st.write(f"**Mentorship Type:** {community.get('mentorship_type', 'Not specified')}")
        st.write(f"**Interested in Events:** {'Yes' if community.get('join_events', False) else 'No'}")
        
        if profile.get('communication_preference'):
            st.write(f"**Communication Preference:** {profile.get('communication_preference')}")
    
    # Add edit profile button
    if st.button("Edit Profile", key="edit_profile"):
        st.session_state['page'] = 'questionnaire'
        st.session_state['show_profile'] = False
        st.rerun()