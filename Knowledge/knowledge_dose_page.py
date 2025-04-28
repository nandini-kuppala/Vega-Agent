import streamlit as st
import json
from datetime import datetime
from Knowledge.knowledge_updater_agent import KnowledgeUpdaterCrew
from backend.database import get_profile
def display_knowledge_dose_page():
    """Display the Daily Knowledge Dose page in Streamlit"""
    
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        st.warning("Please sign in first")
        st.session_state['page'] = 'login'
        st.rerun()
        return
    
    # Page title and greeting
    st.title("Daily Knowledge Dose")
    
    # Get user profile information if available
    user_profile = None
    user_name = "there"  # Default name
    
    if 'user_id' in st.session_state:
        try:
            
            result = get_profile(st.session_state['user_id'])
            if result["status"] == "success":
                user_profile = result["profile"]
                # Try to extract name from profile if available
                if "name" in user_profile:
                    user_name = user_profile["name"]
        except Exception as e:
            st.error(f"Error retrieving profile: {str(e)}")
    
    # Greeting
    current_date = datetime.now().strftime("%B %d, %Y")
    st.markdown(f"### Hello, {user_name}! Here's your knowledge update for {current_date}")
    
    # Create two columns for the main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Initialize session state for knowledge updates if not already done
        if 'knowledge_updates' not in st.session_state:
            st.session_state.knowledge_updates = None
        
        # Display knowledge update content if available
        if st.session_state.knowledge_updates:
            display_knowledge_content(st.session_state.knowledge_updates)
        else:
            st.info("Generate your personalized knowledge update using the form on the right.")
    
    with col2:
        with st.form("knowledge_settings"):
            st.markdown("### Customize Your Knowledge Feed")
            
            # Get default values from user profile
            default_skills = ', '.join(user_profile.get('skills', [])) if user_profile else ''
            
            # Input fields for customization
            skills = st.text_area("Skills", 
                                value=default_skills,
                                help="Enter skills separated by commas (e.g., Python, AI, Cloud Computing)")
            
            industries = st.multiselect("Industries", 
                                       ["Technology", "Healthcare", "Finance", "Education", 
                                        "Manufacturing", "Retail", "Energy", "Media", "Telecommunications",
                                        "Transportation", "Legal", "Consulting", "Non-profit"], 
                                       default=["Technology"])
            
            interests = st.text_area("Interests", 
                                    help="Enter interests separated by commas (e.g., Machine Learning, Cybersecurity)")
            
            # Submit button
            submitted = st.form_submit_button("Generate Knowledge Update", use_container_width=True)
            
            if submitted:
                if not skills:
                    st.error("Please enter at least one skill.")
                    return
                
                # Prepare profile for knowledge update
                candidate_profile = {
                    "skills": [s.strip() for s in skills.split(",") if s.strip()],
                    "industry": ", ".join(industries),
                    "interests": [i.strip() for i in interests.split(",") if i.strip()]
                }
                
                # Merge with user profile if available
                if user_profile:
                    # Keep existing profile items but update with form values
                    merged_profile = {**user_profile}
                    merged_profile["skills"] = candidate_profile["skills"]
                    merged_profile["industry"] = candidate_profile["industry"]
                    merged_profile["interests"] = candidate_profile["interests"]
                    candidate_profile = merged_profile
                
                with st.spinner("Generating your personalized knowledge update..."):
                    try:
                        # Create and run the knowledge updater crew
                        knowledge_updater = KnowledgeUpdaterCrew(api_key=st.secrets["GEMINI_API_KEY"])
                        updates = knowledge_updater.generate_knowledge_update(candidate_profile)
                        
                        # Save updates to session state
                        st.session_state.knowledge_updates = updates
                        
                        # Rerun to display the updates
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error generating knowledge update: {str(e)}")
        
        # Additional options
        if st.session_state.knowledge_updates:
            st.markdown("### Options")
            
            # Save to favorites (placeholder)
            if st.button("💾 Save to Favorites", use_container_width=True):
                st.success("Update saved to favorites!")
            
            # Share (placeholder)
            if st.button("📤 Share", use_container_width=True):
                st.success("Sharing options would appear here!")
            
            # Frequency setting
            st.markdown("### Update Frequency")
            frequency = st.select_slider(
                "How often would you like to receive updates?",
                options=["Daily", "Weekly", "Bi-weekly", "Monthly"]
            )
            
            if st.button("Set Frequency", use_container_width=True):
                st.success(f"You'll now receive updates {frequency.lower()}!")

def display_knowledge_content(updates):
    """Display the knowledge update content in a structured format"""
    
    # Function to create styled sections
    def create_section(title, icon, items, color):
        st.markdown(f"## {icon} {title}")
        
        if not items:
            st.info(f"No {title.lower()} available at this time.")
            return
        
        for i, item in enumerate(items):
            with st.container():
                st.markdown(f"""
                <div style="padding: 10px; border-left: 4px solid {color}; margin-bottom: 15px;">
                    <h3 style="margin: 0; color: {color};">{item.get('headline', '')}</h3>
                    <p>{item.get('description', '')}</p>
                </div>
                """, unsafe_allow_html=True)
    
    # Display each section
    create_section("New Technologies", "🔥", updates["sections"]["tech_updates"], "#FF6B6B")
    create_section("Industry News", "📰", updates["sections"]["industry_news"], "#4ECDC4")
    create_section("Emerging Trends", "📈", updates["sections"]["emerging_trends"], "#FFD166")
    create_section("Recommended Reads", "📚", updates["sections"]["recommended_reads"], "#6A0572")
    
    # Add footer
    st.markdown("""
    <div style="text-align: center; padding: 20px; color: #888; font-size: 0.8em;">
        Knowledge update generated on {date}. Content is AI-generated and may require verification.
    </div>
    """.format(date=updates["date"]), unsafe_allow_html=True)