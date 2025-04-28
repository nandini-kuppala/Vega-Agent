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
from streamlit_extras.stylable_container import stylable_container
from Agentic_ai.roadmap import generate_learning_roadmap
from skill_assessment import skill
from backend.database import get_profile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project root directory to the Python path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
# Import pages
from user_profile.login import login_page
from user_profile.signup import signup_page
from user_profile.questionnaire import questionnaire_page

from utils.design_utils import inject_global_styles

from st_audiorec import st_audiorec

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
            st.error("User ID not found in session state. Please log in again.")
            st.markdown('</div>', unsafe_allow_html=True)
            return            
        
        # Get profile data
        try:
            res = get_profile(st.session_state['user_id'])
            
            if res["status"] == "success":
                profile = res["profile"]
            else:
                st.error("Failed to retrieve profile data.")
                st.markdown('</div>', unsafe_allow_html=True)
                return
        except Exception as e:
            st.error(f"Error retrieving profile: {str(e)}")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        
        # User header with avatar
        st.write(f"## {profile.get('name', 'User')}")
        st.markdown('<div class="profile-header">', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 64px; margin-right: 20px;">👤</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div>
            <p style="margin: 0; font-size: 18px;">{profile.get('education', 'Education not specified')}</p>
            <p style="margin: 0; color: #6c757d;">Experience: {profile.get('experience_years', 0)} years</p>
            <p style="margin: 0; color: #6c757d;">{profile.get('location', {}).get('city', 'Location not specified')}</p>
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
            
            if profile.get('last_job'):
                st.write(f"**Last Position:** {profile['last_job'].get('title', 'Not specified')} at {profile['last_job'].get('company', 'Not specified')}")
            
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
        st.error("User ID not found in session state. Please log in again.")
        return
        
    try:
        res = get_profile(st.session_state['user_id'])
        
        if res["status"] == "success":
            profile = res["profile"]
        else:
            st.error("Failed to retrieve profile data.")
            return
    except Exception as e:
        st.error(f"Error retrieving profile: {str(e)}")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Personal Information")
        st.write(f"**Education:** {profile.get('education', 'Not specified')}")
        st.write(f"**Experience:** {profile.get('experience_years', 0)} years")
        st.write(f"**Current Status:** {profile.get('current_status', 'Not specified')}")
        
        if profile.get('last_job'):
            st.write(f"**Last Job:** {profile['last_job'].get('title', 'Not specified')} at {profile['last_job'].get('company', 'Not specified')}")
        
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


def display_roadmap_page():
    """Display the learning roadmap page"""
    
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        st.warning("Please sign in first")
        st.session_state['page'] = 'login'
        st.rerun()
        return
    
    st.title("Your Learning Roadmap")
    
    # Try to get user profile information
    try:
        # Use direct database function to get profile
        result = get_profile(st.session_state['user_id'])
        
        if result["status"] == "success":
            profile_data = result["profile"]
            
            # Display user information
            st.markdown(f"### Hello! Let's build your personalized learning roadmap")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Your Profile Summary")
                st.write(f"🎓 Education: {profile_data.get('education', 'Not specified')}")
                st.write(f"💼 Experience: {profile_data.get('experience_years', 0)} years")
                
                # Display skills as tags
                if profile_data.get('skills'):
                    st.write("🔧 Current Skills:")
                    skill_html = "<div style='display: flex; flex-wrap: wrap; gap: 8px;'>"
                    for skill in profile_data.get('skills', []):
                        skill_html += f"<span style='background-color: #f0f0f0; padding: 5px 10px; border-radius: 20px; font-size: 14px;'>{skill}</span>"
                    skill_html += "</div>"
                    st.markdown(skill_html, unsafe_allow_html=True)
            
            with col2:
                st.subheader("Career Goals")
                if 'job_preferences' in profile_data and profile_data['job_preferences']:
                    st.write(f"🎯 Short-term: {profile_data['job_preferences'].get('short_term_goal', 'Not specified')}")
                    st.write(f"🚀 Long-term: {profile_data['job_preferences'].get('long_term_goal', 'Not specified')}")
                    
                    # Display preferred roles
                    if 'roles' in profile_data['job_preferences']:
                        st.write("👔 Preferred Roles:")
                        roles_html = "<div style='display: flex; flex-wrap: wrap; gap: 8px;'>"
                        for role in profile_data['job_preferences']['roles']:
                            roles_html += f"<span style='background-color: #e6f3ff; padding: 5px 10px; border-radius: 20px; font-size: 14px;'>{role}</span>"
                        roles_html += "</div>"
                        st.markdown(roles_html, unsafe_allow_html=True)
                else:
                    st.info("Please complete your profile to view career goals")
            
            # Learning goal input
            st.markdown("### What's your learning goal?")
            
            # Default learning goal based on profile
            default_goal = ""
            if 'job_preferences' in profile_data and profile_data['job_preferences'].get('short_term_goal'):
                default_goal = profile_data['job_preferences'].get('short_term_goal')
            
            # Add some predefined learning goals to choose from
            goal_options = [
                "I want to become a Machine Learning Engineer",
                "I want to specialize in Natural Language Processing",
                "I want to become a Full Stack Developer",
                "I want to learn Data Science and Analytics",
                "I want to become a DevOps Engineer",
                "Custom Goal"
            ]
            
            # Goal selection
            selected_goal = st.selectbox("Select a learning goal", options=goal_options)
            
            if selected_goal == "Custom Goal":
                custom_goal = st.text_area("Enter your custom learning goal", 
                                          value=default_goal, 
                                          height=100, 
                                          placeholder="E.g., I want to become a proficient AI engineer...")
                learning_goal = custom_goal
            else:
                learning_goal = selected_goal
            
            # Format the user profile data for the roadmap generator
            user_profile_text = f"""
            Name: {st.session_state.get('username', 'User')}
            Education: {profile_data.get('education', 'Not specified')}
            
            Skills:
            {', '.join(profile_data.get('skills', ['None specified']))}
            
            Experience: {profile_data.get('experience_years', 0)} years
            """
            
            if profile_data.get('last_job'):
                user_profile_text += f"""
                Last Job: {profile_data['last_job'].get('title', 'Not specified')} at {profile_data['last_job'].get('company', 'Not specified')}
                """
            
            # Generate roadmap button
            if st.button("Generate Learning Roadmap", type="primary"):
                if learning_goal:
                    with st.spinner("Generating your personalized learning roadmap... This may take a few minutes."):
                        try:
                            # Call the CrewAI function to generate the roadmap
                            roadmap = generate_learning_roadmap(user_profile_text, learning_goal)
                            
                            # Store the roadmap in session state
                            st.session_state['current_roadmap'] = roadmap
                            
                            # Display the roadmap
                            st.markdown("## Your Personalized Learning Roadmap")
                            st.markdown(roadmap)
                            
                            # Add a download button for the markdown file
                            st.download_button(
                                label="Download Roadmap",
                                data=roadmap,
                                file_name="my_learning_roadmap.md",
                                mime="text/markdown"
                            )
                            
                        except Exception as e:
                            st.error(f"Error generating roadmap: {str(e)}")
                else:
                    st.warning("Please enter a learning goal first")
            
            # Display previously generated roadmap if it exists
            if 'current_roadmap' in st.session_state and not st.button:
                st.markdown("## Your Personalized Learning Roadmap")
                st.markdown(st.session_state['current_roadmap'])
                
                # Add a download button for the markdown file
                st.download_button(
                    label="Download Roadmap", 
                    data=st.session_state['current_roadmap'],
                    file_name="my_learning_roadmap.md",
                    mime="text/markdown"
                )
        
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
        ## Complete Your Profile
        
        To generate a personalized learning roadmap, we need to know more about you.
        Please complete your profile questionnaire first.
        """)
        
        if st.button("Complete Your Profile"):
            st.session_state['page'] = 'questionnaire'
            st.rerun()

    # Navigation buttons at bottom
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🏠 Home", key="home_from_roadmap", use_container_width=True):
            st.session_state['page'] = 'home'
            st.rerun()
            
    with col2:
        if st.button("💬 Chat with ASHA", key="chat_from_roadmap", use_container_width=True):
            st.session_state['page'] = 'chat'
            st.rerun()

def transcribe_audio(audio_data):
    """Transcribe audio using Sarvam AI API"""
    api_key = "0535ffaa-546d-4fd0-a380-ee76948e0d14"
    url = "https://api.sarvam.ai/speech-to-text-translate"
    import tempfile
    import os

    # Create a temporary file with proper permissions and cleanup management
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio_file:
        try:
            # Write the audio data to the temporary file
            temp_audio_file.write(audio_data)
            temp_audio_file.flush()
            temp_audio_path = temp_audio_file.name
            
            # Close the file before passing it to the API
            temp_audio_file.close()
            
            headers = {
                "api-subscription-key": api_key
            }
            
            # Set the correct MIME type explicitly
            files = {
                'file': ('audio.wav', open(temp_audio_path, 'rb'), 'audio/wav')
            }
            
            data = {
                'with_diarization': 'false',
                'num_speakers': '1'
            }
            
            response = requests.post(url, headers=headers, files=files, data=data)
            
            # Debug info without displaying to user
            print(f"Transcription response status: {response.status_code}")
            print(f"Response content: {response.text}")
            
            if response.status_code != 200:
                logger.error(f"Transcription failed: {response.text}")
                return ""
                
            result = response.json()
            
            # Extract the transcript from the response
            if 'text' in result:
                return result['text']
            elif 'transcript' in result:
                return result['transcript']
            else:
                logger.error(f"Unexpected response format: {result}")
                return ""
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return ""
        finally:
            # Make sure to clean up the temp file
            try:
                if os.path.exists(temp_audio_path):
                    os.unlink(temp_audio_path)
            except Exception as e:
                logger.error(f"Error removing temporary file: {str(e)}")


def detect_language(text):
    """Detect the language of input text using Sarvam AI API"""
    import requests

    url = "https://api.sarvam.ai/text-lid"

    payload = {"input": text}
    headers = {
        "api-subscription-key": "0535ffaa-546d-4fd0-a380-ee76948e0d14",
        "Content-Type": "application/json"
    }

    try:
        response = requests.request("POST", url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        # Extract language code
        language_code = result.get("language_code")
        return language_code
        
    except Exception as e:
        logger.error(f"Language detection error: {str(e)}")
        return "en-IN"  # Default to English if detection fails
 

def translate_text(text, source_language, target_language):
    """Translate text using Sarvam AI API"""
    import requests
    
    # If languages are the same or text is empty, return the original text
    if source_language == target_language or not text:
        return text
    
    url = "https://api.sarvam.ai/translate"
    
    payload = {
        "enable_preprocessing": False,
        "input": text,
        "source_language_code": source_language,
        "target_language_code": target_language,
        "speaker_gender": "Female",
        "mode": "formal",
        "output_script": "spoken-form-in-native",
        "numerals_format": "international"
    }
    
    headers = {
        "api-subscription-key": "0535ffaa-546d-4fd0-a380-ee76948e0d14",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        # Extract the translated text
        if 'translated_text' in result:
            return result['translated_text']
        else:
            logger.error(f"Translation failed: Invalid response format - {result}")
            return text  # Return original text if translation fails
            
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return text  # Return original text if translation fails

def process_user_query(prompt):
    """Process the user query and generate a response"""
    # Check if user is set
    if not st.session_state.get('user_id'):
        with st.chat_message("assistant", avatar="👩‍💼"):
            content = "It seems you're not logged in. Please log in first so I can provide personalized assistance."
            st.markdown(content)
            st.session_state.messages.append({"role": "assistant", "content": content, "feedback": None})
            return
    
    # Generate response with the assistant
    with st.chat_message("assistant", avatar="👩‍💼"):
        with st.spinner("Thinking..."):
            try:
                # Process the query using our CareerGuidanceChatbot
                assistant = st.session_state.get('assistant')
                response = assistant.process_query(prompt)
                
                # Check if we need to translate the response
                if hasattr(st.session_state, 'detected_language') and st.session_state.detected_language != "en-IN":
                    translated_response = translate_text(
                        response, 
                        "en-IN", 
                        st.session_state.detected_language
                    )
                    display_response = translated_response
                else:
                    display_response = response
                
                # Update chat history
                st.markdown(display_response)
                st.session_state.messages.append({"role": "assistant", "content": display_response, "feedback": None})
                
            except Exception as e:
                error_msg = f"I'm sorry, I encountered an error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg, "feedback": None})
                logger.error(f"Error generating response: {str(e)}")
                logger.error(traceback.format_exc())

def display_chat_page():
    """Display a chat interface with ASHA AI with quick action options and voice input"""
    
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        st.warning("Please sign in first")
        st.session_state['page'] = 'login'
        st.rerun()
        return
    
    st.title("ASHA AI Chat")
    
    # Initialize chat history if it doesn't exist
    if 'messages' not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! I'm ASHA, your career assistant powered by AI. How can I help you today?", "feedback": None}
        ]
    
    # Create a container for the chat messages to ensure they stay above the input
    chat_container = st.container()
    
    # Create a container for the input area which will always be at the bottom
    input_container = st.container()
    
    # Display quick action buttons above chat messages
    with chat_container:
        st.markdown("""
        <style>
        .quick-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 15px;
        }
        .quick-action-button {
            background-color: #f0f0f0;
            border-radius: 20px;
            padding: 8px 15px;
            font-size: 14px;
            cursor: pointer;
            border: none;
            transition: background-color 0.3s;
        }
        .quick-action-button:hover {
            background-color: #e0e0e0;
        }
        .voice-button {
            background-color: #f0f0f0;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            border: none;
            transition: background-color 0.3s;
            margin-right: 10px;
        }
        .voice-button:hover {
            background-color: #e0e0e0;
        }
        .voice-button.recording {
            background-color: #ff5252;
        }
        .input-container {
            display: flex;
            align-items: center;
            margin-top: 10px;
            position: fixed;
            bottom: 0;
            width: 100%;
        }
        .stAudioRecorderWrapper {
            display: none !important;
        }
        .custom-recording-indicator {
            color: red;
            font-weight: bold;
            margin-top: 5px;
        }
        .stChatInputContainer {
            position: fixed;
            bottom: 0;
            width: 100%;
            background-color: white;
            padding: 10px 0;
            z-index: 999;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="quick-actions">', unsafe_allow_html=True)
        
        col1, col2, col3,col4 = st.columns(4)
        
        with col1:
            if st.button("🔍 Find Latest Job Postings", key="find_jobs"):
                with st.spinner("Searching for jobs..."):
                    try:
                        assistant = st.session_state.get('assistant')
                        response = assistant._get_job_recommendations()
                        st.session_state.messages.append({"role": "user", "content": "Find me latest job postings for you"})
                        st.session_state.messages.append({"role": "assistant", "content": response, "feedback": None})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error finding jobs: {str(e)}")
        
        with col2:
            if st.button("🎯 Find Upcoming Events", key="find_events"):
                with st.spinner("Discovering events..."):
                    try:
                        assistant = st.session_state.get('assistant')
                        response = assistant._get_event_recommendations()
                        st.session_state.messages.append({"role": "user", "content": "Find upcoming events for you"})
                        st.session_state.messages.append({"role": "assistant", "content": response, "feedback": None})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error finding events: {str(e)}")
        
        with col3:
            if st.button("👥 Find Community Groups", key="find_groups"):
                with st.spinner("Discovering community groups..."):
                    try:
                        assistant = st.session_state.get('assistant')
                        response = assistant._get_community_recommendations()
                        st.session_state.messages.append({"role": "user", "content": "Find community groups for you"})
                        st.session_state.messages.append({"role": "assistant", "content": response, "feedback": None})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error finding community groups: {str(e)}")

        with col4:
            if st.button("🧑‍🏫 Find Workshops and sessions", key="find_sessions"):
                with st.spinner("Discovering sessions..."):
                    try:
                        assistant = st.session_state.get('assistant')
                        response = assistant._get_session_recommendations()
                        st.session_state.messages.append({"role": "user", "content": "Find Workshops and sessions for you"})
                        st.session_state.messages.append({"role": "assistant", "content": response, "feedback": None})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error finding Workshops and sessions: {str(e)}")
        
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Display chat messages with feedback buttons
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"], avatar="👩‍💼" if message["role"] == "assistant" else None):
                st.markdown(message["content"])
                
                # Add feedback buttons only for assistant messages
                if message["role"] == "assistant" and i > 0:
                    cols = st.columns([0.05, 0.05, 0.9])
                    
                    # Add feedback status if already provided
                    if message.get("feedback") is not None:
                        if message["feedback"] == "positive":
                            cols[0].markdown("👍")
                        else:
                            cols[1].markdown("👎")
                    else:
                        # Thumbs up button
                        if cols[0].button("👍", key=f"thumbs_up_{i}"):
                            message["feedback"] = "positive"
                            # Store feedback in session state
                            if "feedback_data" not in st.session_state:
                                st.session_state.feedback_data = []
                            
                            st.session_state.feedback_data.append({
                                "message_id": i,
                                "content": message["content"],
                                "feedback": "positive",
                                "timestamp": datetime.now().isoformat()
                            })
                            st.rerun()
                        
                        # Thumbs down button
                        if cols[1].button("👎", key=f"thumbs_down_{i}"):
                            message["feedback"] = "negative"
                            # Store feedback in session state
                            if "feedback_data" not in st.session_state:
                                st.session_state.feedback_data = []
                                
                            st.session_state.feedback_data.append({
                                "message_id": i,
                                "content": message["content"],
                                "feedback": "negative",
                                "timestamp": datetime.now().isoformat()
                            })
                            st.rerun()
    
    # Create a spacer to ensure content is visible above the fixed input bar
    st.markdown("<div style='padding-bottom: 80px;'></div>", unsafe_allow_html=True)
    
    # Input area always at the bottom
    with input_container:
        # Create columns for the chat input and voice button
        col1, col2 = st.columns([0.9, 0.1])
        
        with col2:
            # Initialize recording state
            if 'is_recording' not in st.session_state:
                st.session_state.is_recording = False
                st.session_state.audio_recorder_key = 0
            
            # Voice button with different style based on recording state
            button_style = "background-color: #ff5252;" if st.session_state.is_recording else "background-color: #f0f0f0;"
            button_text = "🛑" if st.session_state.is_recording else "🎤"
            
            if st.button(button_text, key="voice_button", help="Toggle voice recording"):
                st.session_state.is_recording = not st.session_state.is_recording
                st.session_state.audio_recorder_key += 1
                st.rerun()
            
            # Show recording indicator
            if st.session_state.is_recording:
                st.markdown("<div class='custom-recording-indicator'>Recording...</div>", unsafe_allow_html=True)
            
            # Hidden audio recorder that's only active when recording
            if st.session_state.is_recording:
                try:
                    wav_audio_data = st_audiorec()
                    
                    if wav_audio_data is not None and wav_audio_data != st.session_state.get('last_audio_data'):
                        st.session_state['last_audio_data'] = wav_audio_data
                        st.session_state.is_recording = False  # Stop recording
                        
                        with st.spinner("Processing your voice input..."):
                            # Transcribe the audio to text
                            transcribed_text = transcribe_audio(wav_audio_data)
                            
                            if transcribed_text:
                                # Detect language
                                detected_lang = detect_language(transcribed_text)
                                st.session_state.detected_language = detected_lang
                                
                                # Translate to English if not already in English
                                if detected_lang != "en-IN":
                                    english_text = translate_text(transcribed_text, detected_lang, "en-IN")
                                else:
                                    english_text = transcribed_text
                                
                                # Add user message to chat history
                                st.session_state.messages.append({"role": "user", "content": transcribed_text})
                                
                                # Generate assistant response
                                with st.spinner("Generating response..."):
                                    try:
                                        # Process the query using our CareerGuidanceChatbot
                                        assistant = st.session_state.get('assistant')
                                        response = assistant.process_query(english_text)
                                        
                                        # Translate back to original language if needed
                                        if detected_lang != "en-IN":
                                            translated_response = translate_text(response, "en-IN", detected_lang)
                                            display_response = translated_response
                                        else:
                                            display_response = response
                                        
                                        # Add assistant response to chat history
                                        st.session_state.messages.append({
                                            "role": "assistant", 
                                            "content": display_response,
                                            "feedback": None
                                        })
                                        
                                        st.rerun()
                                    except Exception as e:
                                        error_msg = f"I'm sorry, I encountered an error: {str(e)}"
                                        st.session_state.messages.append({
                                            "role": "assistant", 
                                            "content": error_msg,
                                            "feedback": None
                                        })
                                        st.rerun()
                except Exception as e:
                    st.error(f"Error with audio recording: {str(e)}")
        
        with col1:
            prompt = st.chat_input("What would you like help with?")
            
            if prompt:
                # Add user message to chat history
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                # Check if user is set
                if not st.session_state.get('user_id'):
                    content = "It seems you're not logged in. Please log in first so I can provide personalized assistance."
                    st.session_state.messages.append({"role": "assistant", "content": content, "feedback": None})
                    st.rerun()
                
                # Detect language of the input
                detected_lang = detect_language(prompt)
                st.session_state.detected_language = detected_lang
                
                # Translate to English if needed
                if detected_lang != "en-IN":
                    english_prompt = translate_text(prompt, detected_lang, "en-IN")
                else:
                    english_prompt = prompt
                
                # Generate response with the assistant
                with st.spinner("Thinking..."):
                    try:
                        # Process the query using our CareerGuidanceChatbot
                        assistant = st.session_state.get('assistant')
                        response = assistant.process_query(english_prompt)
                        
                        # Translate back to original language if needed
                        if detected_lang != "en-IN":
                            translated_response = translate_text(response, "en-IN", detected_lang)
                            display_response = translated_response
                        else:
                            display_response = response
                        
                        # Update chat history
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": display_response,
                            "feedback": None
                        })
                        st.rerun()
                        
                    except Exception as e:
                        error_msg = f"I'm sorry, I encountered an error: {str(e)}"
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": error_msg,
                            "feedback": None
                        })
                        logger.error(f"Error generating response: {str(e)}")
                        logger.error(traceback.format_exc())
                        st.rerun()


def main():
    # Configure page
    st.set_page_config(
        page_title="ASHA AI Bot",
        page_icon="👩‍💼",
        layout="wide",
        initial_sidebar_state="collapsed"
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
    # Store authentication in browser cache to persist across page refreshes
    if 'authenticated' in st.session_state and st.session_state['authenticated']:
        st.session_state['user_authenticated'] = True
        st.session_state['user_id'] = st.session_state.get('user_id', '')
        st.session_state['token'] = st.session_state.get('token', '')
    
    # Check for cached authentication on page load
    if not st.session_state.get('authenticated') and st.session_state.get('user_authenticated'):
        st.session_state['authenticated'] = True
        st.session_state['user_id'] = st.session_state.get('user_id', '')
        st.session_state['token'] = st.session_state.get('token', '')
        st.session_state['page'] = st.session_state.get('page', 'home')

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
                st.session_state['assistant'].get_profile(user_id=st.session_state['user_id'])
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

            if st.button("📝 Complete Profile", key="profile_btn", use_container_width=True):
                st.session_state['page'] = 'questionnaire'
                st.session_state['show_profile'] = False
                st.rerun()

            if st.button("💬 Chat", key="chat_btn", use_container_width=True):
                st.session_state['page'] = 'chat'
                st.session_state['show_profile'] = False
                st.rerun()

            if st.button("🚀 Your Roadmap", key="roadmap", use_container_width=True):
                st.session_state['page'] = 'roadmap'
                st.session_state['show_profile'] = False
                st.rerun()

            if st.button("📄 Resume Builder", key="resume", use_container_width=True):
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
                        🧠 Skill Assessment
                    </button>
                </a>
                """,
                unsafe_allow_html=True
            )

    
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
    elif page == 'home':
        display_home_page()
    elif page == 'chat':
        display_chat_page()
    elif page == 'roadmap':
        display_roadmap_page()
    else:
        st.error("Page not found!")
        st.session_state['page'] = 'login'
        st.rerun()


if __name__ == "__main__":
    main()
