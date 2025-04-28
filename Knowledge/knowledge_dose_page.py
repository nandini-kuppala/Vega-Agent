import streamlit as st
import json
import random
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from Knowledge.knowledge_updater_agent import KnowledgeUpdaterCrew
import time
from backend.database import get_profile

def display_daily_knowledge_page():
    """Display the Daily Knowledge Dose page in Streamlit"""
    
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        st.warning("Please sign in first")
        st.session_state['page'] = 'login'
        st.rerun()
        return
    
    st.title("🧠 Daily Knowledge Dose")
    
    # Initialize session state for knowledge updates
    if 'knowledge_updates' not in st.session_state:
        st.session_state.knowledge_updates = None
    if 'last_update_time' not in st.session_state:
        st.session_state.last_update_time = None
    
    # Get user profile information if available
    user_profile = None
    if 'user_id' in st.session_state:
        try:
            
            result = get_profile(st.session_state['user_id'])
            if result["status"] == "success":
                user_profile = result["profile"]
        except Exception as e:
            st.error(f"Error retrieving profile: {str(e)}")
    
    # If no user profile is available, show a message
    if not user_profile:
        st.warning("Please complete your profile to get personalized knowledge updates.")
        if st.button("Complete Your Profile"):
            st.session_state['page'] = 'questionnaire'
            st.rerun()
        return
    
    # Display greeting
    user_name = ""
    if 'personal_info' in user_profile and 'name' in user_profile['personal_info']:
        user_name = user_profile['personal_info']['name']
    
    current_hour = datetime.now().hour
    greeting = "Good morning" if 5 <= current_hour < 12 else "Good afternoon" if 12 <= current_hour < 18 else "Good evening"
    
    if user_name:
        st.markdown(f"### {greeting}, {user_name}! 👋")
    else:
        st.markdown(f"### {greeting}! 👋")
    
    # Display personalization message
    skills = user_profile.get('skills', [])
    skill_text = ", ".join(skills[:3]) if skills else "your interests"
    
    st.markdown(f"""
    Here's your personalized knowledge update based on {skill_text}. 
    Stay informed about the latest in your field!
    """)
    
    # Create a container for controls
    control_col1, control_col2 = st.columns([3, 1])
    
    with control_col1:
        # Show last update time if available
        if st.session_state.last_update_time:
            st.caption(f"Last updated: {st.session_state.last_update_time}")
    
    with control_col2:
        # Refresh button
        if st.button("🔄 Refresh Feed", type="primary", use_container_width=True):
            with st.spinner("Fetching personalized updates..."):
                try:
                    # Initialize knowledge updater
                    knowledge_updater = KnowledgeUpdaterCrew(
                        serper_api_key=st.secrets["SERPER_API_KEY"],
                        gemini_api_key=st.secrets["GEMINI_API_KEY"]
                    )
                    
                    # For production
                    if st.secrets.get("USE_MOCK_DATA", "false").lower() == "true":
                        updates = knowledge_updater.get_mock_updates(user_profile)
                    else:
                        updates = knowledge_updater.get_knowledge_updates(user_profile)
                    
                    # Store updates in session state
                    st.session_state.knowledge_updates = updates
                    st.session_state.last_update_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")
                    
                    st.success("Updates refreshed successfully!")
                    time.sleep(1)  # Short delay for better UX
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error fetching updates: {str(e)}")
    
    # Horizontal line
    st.markdown("---")
    
    # If no updates are available yet, use mock data or show placeholder
    if not st.session_state.knowledge_updates:
        # For initial load, get mock data
        try:
            with st.spinner("Preparing your personalized feed..."):
                knowledge_updater = KnowledgeUpdaterCrew(
                    serper_api_key=st.secrets["SERPER_API_KEY"],
                    gemini_api_key=st.secrets["GEMINI_API_KEY"]
                )
                updates = knowledge_updater.get_mock_updates(user_profile)
                st.session_state.knowledge_updates = updates
                st.session_state.last_update_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        except Exception as e:
            st.error(f"Error creating initial feed: {str(e)}")
            return
    
    # Display updates if available
    if st.session_state.knowledge_updates:
        updates = st.session_state.knowledge_updates
        
        # Define tab labels with icons
        tabs = st.tabs([
            "🔥 New Technologies", 
            "📰 Industry News", 
            "📈 Emerging Trends", 
            "📚 Recommended Reads"
        ])
        
        # New Technologies Tab
        with tabs[0]:
            if "New Technologies" in updates and updates["New Technologies"]:
                display_content_cards(updates["New Technologies"])
            else:
                st.info("No technology updates available at the moment.")
        
        # Industry News Tab
        with tabs[1]:
            if "Industry News" in updates and updates["Industry News"]:
                display_content_cards(updates["Industry News"])
            else:
                st.info("No industry news available at the moment.")
        
        # Emerging Trends Tab
        with tabs[2]:
            if "Emerging Trends" in updates and updates["Emerging Trends"]:
                display_content_cards(updates["Emerging Trends"])
            else:
                st.info("No trend updates available at the moment.")
        
        # Recommended Reads Tab
        with tabs[3]:
            if "Recommended Reads" in updates and updates["Recommended Reads"]:
                display_resource_cards(updates["Recommended Reads"])
            else:
                st.info("No reading recommendations available at the moment.")
    
    else:
        st.info("Click the Refresh Feed button to get personalized knowledge updates.")

def display_content_cards(items):
    """Display content items as cards"""
    # Use a 2-column layout for items
    cols = st.columns(2)
    
    for i, item in enumerate(items):
        col = cols[i % 2]
        with col:
            # Create a card-like container with border
            with st.container():
                st.markdown(f"""
                <div style="border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 15px;">
                """, unsafe_allow_html=True)
                
                # Title with link
                st.markdown(f"#### [{item.get('title', 'No Title')}]({item.get('url', '#')})")
                
                # Image if available
                if 'image' in item and item['image']:
                    st.image(item['image'], use_column_width=True)
                
                # Description
                if 'description' in item:
                    st.markdown(item['description'])
                
                # Date and metadata in smaller text
                meta_text = []
                if 'date' in item and item['date']:
                    meta_text.append(f"📅 {item['date']}")
                if 'source' in item:
                    meta_text.append(f"🔗 {item['source']}")
                
                if meta_text:
                    st.caption(" | ".join(meta_text))
                
                # Personalization note in highlighted box if available
                if 'personalization' in item:
                    st.markdown(f"""
                    <div style="background-color: #f0f7ff; border-left: 3px solid #3b83f6; padding: 10px; font-size: 0.9em;">
                        <strong>Why this matters to you:</strong> {item['personalization']}
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)

def display_resource_cards(items):
    """Display resource items as cards"""
    # Use a single column layout for resource items
    for item in items:
        with st.container():
            st.markdown(f"""
            <div style="border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 15px;">
            """, unsafe_allow_html=True)
            
            # Title with link and resource type badge
            resource_type = item.get('type', 'Resource')
            badge_color = {
                "Article": "#28a745",
                "Tutorial": "#fd7e14",
                "Research Paper": "#007bff",
                "Course": "#6f42c1",
                "GitHub Repository": "#6c757d"
            }.get(resource_type, "#6c757d")
            
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h4 style="margin: 0;">
                    <a href="{item.get('url', '#')}" target="_blank">{item.get('title', 'No Title')}</a>
                </h4>
                <span style="background-color: {badge_color}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.8em;">
                    {resource_type}
                </span>
            </div>
            """, unsafe_allow_html=True)
            
            # Description
            if 'description' in item:
                st.markdown(item['description'])
            
            # Author and metadata
            meta_text = []
            if 'author' in item and item['author']:
                meta_text.append(f"👤 {item['author']}")
            if 'date' in item and item['date']:
                meta_text.append(f"📅 {item['date']}")
            
            if meta_text:
                st.caption(" | ".join(meta_text))
            
            # Personalization note in highlighted box if available
            if 'personalization' in item:
                st.markdown(f"""
                <div style="background-color: #f0f7ff; border-left: 3px solid #3b83f6; padding: 10px; font-size: 0.9em;">
                    <strong>Why this matters to you:</strong> {item['personalization']}
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Add a "Read Now" button
            if st.button(f"📖 Read Now", key=f"read_{items.index(item)}"):
                # Open the URL in a new tab (this doesn't actually work in Streamlit but shows intent)
                js = f"window.open('{item.get('url', '#')}')"
                st.markdown(f'<script>{js}</script>', unsafe_allow_html=True)
                st.write(f"Opening {item.get('title', 'resource')}...")