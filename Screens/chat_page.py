
import streamlit as st
import requests
import traceback
import logging
from datetime import datetime
from st_audiorec import st_audiorec
from backend.database import save_chat_history, get_chat_history, sanitize_response,get_user_chat_sessions, get_chat_session, save_session_messages, delete_chat_session, create_chat_session, update_session_title

import json


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
            if st.session_state.get('current_session_id'):
                save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
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
                if st.session_state.get('current_session_id'):
                    save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
                
            except Exception as e:
                error_msg = f"I'm sorry, I encountered an error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg, "feedback": None})
                if st.session_state.get('current_session_id'):
                    save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
                logger.error(f"Error generating response: {str(e)}")
                logger.error(traceback.format_exc())


def display_chat_page():
    """Display a chat interface with session management in popup panel instead of sidebar"""
    
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        st.warning("Please sign in first")
        st.session_state['page'] = 'login'
        st.rerun()
        return
    
    user_id = st.session_state.get('user_id')
    current_session_id = st.session_state.get('current_session_id')
    
    # Initialize popup state
    if 'session_popup_open' not in st.session_state:
        st.session_state.session_popup_open = False
    
    # Add CSS styling for popup panel and chat interface
    st.markdown("""
    <style>
    /* Chat session styling */
    .chat-session-container {
        border-radius: 8px;
        padding: 8px;
        margin: 4px 0;
        transition: background-color 0.2s;
    }

    .chat-session-container:hover {
        background-color: #f0f0f0;
    }

    .chat-session-active {
        background-color: #e3f2fd;
        border-left: 3px solid #2196f3;
    }

    /* Session Manager Popup styling */
    .session-popup {
        position: fixed;
        top: 50%;
        right: 40px;
        transform: translateY(-50%);
        width: 340px;
        max-height: 80vh;
        background-color: white;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        border-radius: 12px;
        padding: 20px;
        overflow-y: auto;
        z-index: 1000;
        display: block;
        opacity: 1;
        transition: opacity 0.3s ease, transform 0.3s ease;
    }

    .session-popup.hidden {
        opacity: 0;
        transform: translateY(-50%) translateX(400px);
        pointer-events: none;
    }

    .popup-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
        border-bottom: 1px solid #eee;
        padding-bottom: 10px;
    }
    
    .popup-title {
        font-size: 18px;
        font-weight: 600;
        margin: 0;
    }
    
    .popup-close {
        background: none;
        border: none;
        font-size: 18px;
        cursor: pointer;
        color: #666;
    }
    
    .popup-close:hover {
        color: #333;
    }

    /* Floating popup toggle button */
    .popup-toggle-btn {
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: #f8f9fa;
        color: #333;
        border: 1px solid #ddd;
        border-radius: 50%;
        width: 44px;
        height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        z-index: 999;
        transition: all 0.2s;
    }
    
    .popup-toggle-btn:hover {
        background-color: #e9ecef;
        box-shadow: 0 3px 8px rgba(0,0,0,0.15);
    }
    
    .popup-toggle-btn.active {
        background-color: #e3f2fd;
        color: #1976d2;
        border-color: #bbdefb;
    }

    .session-preview {
        font-size: 12px;
        color: #666;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-top: -12px;
        margin-bottom: 4px;
    }

    .session-date {
        font-size: 11px;
        color: #888;
        text-align: right;
        margin-top: -10px;
        margin-bottom: 4px;
    }

    .session-list {
        max-height: calc(80vh - 120px);
        overflow-y: auto;
        padding-right: 5px;
    }
    
    .session-list::-webkit-scrollbar {
        width: 5px;
    }
    
    .session-list::-webkit-scrollbar-thumb {
        background-color: #ddd;
        border-radius: 10px;
    }
    
    .session-list::-webkit-scrollbar-track {
        background-color: #f5f5f5;
    }

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
    
    .custom-recording-indicator {
        color: red;
        font-weight: bold;
        margin-top: 5px;
    }
    
    .session-title {
        font-size: 14px;
        font-weight: 500;
        color: #333;
        text-align: left;
        padding: 8px 12px;
        border-radius: 6px;
        border: none;
        background: none;
        width: 100%;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    
    .session-title:hover {
        background-color: #f5f5f5;
    }
    
    .session-title.active {
        background-color: #e3f2fd;
        color: #1976d2;
        font-weight: 600;
    }
    
    .delete-button {
        color: #d32f2f;
    }
    
    .delete-button:hover {
        background-color: #ffebee;
        border-color: #d32f2f;
    }
    
    .session-item {
        border-bottom: 1px solid #eee;
        padding: 10px 0;
        margin-bottom: 5px;
    }
    
    .new-chat-btn {
        width: 100%;
        background-color: #f5f5f5;
        border: 1px solid #ddd;
        padding: 8px 15px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        font-weight: 500;
        margin-bottom: 15px;
        transition: all 0.2s;
    }
    
    .new-chat-btn:hover {
        background-color: #e9ecef;
    }
    
    .action-btn {
        background: none;
        border: none;
        cursor: pointer;
        color: #666;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
        transition: all 0.2s;
    }
    
    .action-btn:hover {
        background-color: #f5f5f5;
        color: #333;
    }
    
    .fixed-input {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        padding: 15px;
        background: white;
        box-shadow: 0 -2px 5px rgba(0,0,0,0.1);
        z-index: 999;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create main layout
    main_col = st.container()
    
    with main_col:
        # Main chat area
        st.markdown('<div class="chat-area">', unsafe_allow_html=True)
        
        # Title area
        st.markdown(
            """
            <div class="title-container">
                <h1>ASHA AI Chat Bot</h1>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Floating toggle button for session popup
        popup_btn_class = "popup-toggle-btn active" if st.session_state.session_popup_open else "popup-toggle-btn"
        st.markdown(
            f"""
            <div class="{popup_btn_class}" id="popupToggleBtn" onclick="toggleSessionPopup()">
                <span>💬</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Initialize or create session if needed
        if not current_session_id:
            result = create_chat_session(user_id)
            if result["status"] == "success":
                st.session_state['current_session_id'] = result["session_id"]
                current_session_id = result["session_id"]
                # Update URL
                current_params = dict(st.query_params)
                current_params['session_id'] = current_session_id
                st.query_params.update(current_params)
        
        # Load current session messages if not already loaded
        if 'messages' not in st.session_state and current_session_id:
            session_data = get_chat_session(current_session_id)
            if session_data["status"] == "success":
                st.session_state['messages'] = session_data["session"]["messages"]
            else:
                st.session_state['messages'] = [{
                    "role": "assistant", 
                    "content": "Hi! I'm ASHA, your career assistant powered by AI. How can I help you today?", 
                    "feedback": None
                }]
        elif 'messages' not in st.session_state:
            st.session_state['messages'] = [{
                "role": "assistant", 
                "content": "Hi! I'm ASHA, your career assistant powered by AI. How can I help you today?", 
                "feedback": None
            }]
        
        # Create a container for the chat messages
        chat_container = st.container()
        
        # Create a container for the input area
        input_container = st.container()
        
        # Display quick action buttons above chat messages
        with chat_container:
            st.markdown('<div class="quick-actions">', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("🔍 Find Latest Job Postings", key="find_jobs"):
                    with st.spinner("Searching for jobs..."):
                        try:
                            assistant = st.session_state.get('assistant')
                            response = assistant._get_job_recommendations()
                            st.session_state.messages.append({"role": "user", "content": "Find me latest job postings for you", "feedback": None})
                            st.session_state.messages.append({"role": "assistant", "content": response, "feedback": None})
                            if st.session_state.get('current_session_id'):
                                save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error finding jobs: {str(e)}")
            
            with col2:
                if st.button("🎯 Find Upcoming Events", key="find_events"):
                    with st.spinner("Discovering events..."):
                        try:
                            assistant = st.session_state.get('assistant')
                            response = assistant._get_event_recommendations()
                            st.session_state.messages.append({"role": "user", "content": "Find upcoming events for you", "feedback": None})
                            st.session_state.messages.append({"role": "assistant", "content": response, "feedback": None})
                            if st.session_state.get('current_session_id'):
                                save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error finding events: {str(e)}")
            
            with col3:
                if st.button("👥 Find Community Groups", key="find_groups"):
                    with st.spinner("Discovering community groups..."):
                        try:
                            assistant = st.session_state.get('assistant')
                            response = assistant._get_community_recommendations()
                            st.session_state.messages.append({"role": "user", "content": "Find community groups for you", "feedback": None})
                            st.session_state.messages.append({"role": "assistant", "content": response, "feedback": None})
                            if st.session_state.get('current_session_id'):
                                save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error finding community groups: {str(e)}")

            with col4:
                if st.button("🧑‍🏫 Find Workshops and sessions", key="find_sessions"):
                    with st.spinner("Discovering sessions..."):
                        try:
                            assistant = st.session_state.get('assistant')
                            response = assistant._get_session_recommendations()
                            st.session_state.messages.append({"role": "user", "content": "Find Workshops and sessions for you", "feedback": None})
                            st.session_state.messages.append({"role": "assistant", "content": response, "feedback": None})
                            if st.session_state.get('current_session_id'):
                                save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
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
                                try:
                                    # Save session messages
                                    save_result = save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
                                    if save_result["status"] == "error":
                                        # Log the error but don't stop the app
                                        print(f"Warning: Failed to save session messages: {save_result['message']}")
                                except Exception as e:
                                    # Log error but allow the chat to continue working
                                    print(f"Error saving session messages: {str(e)}")
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
                                if st.session_state.get('current_session_id'):
                                    save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
                                st.rerun()
        
        # Create a spacer to ensure content is visible above the fixed input bar
        st.markdown("<div style='padding-bottom: 80px;'></div>", unsafe_allow_html=True)
        
        # Fixed input area at the bottom
        with input_container:
            st.markdown('<div class="fixed-input">', unsafe_allow_html=True)
            # Create columns for the chat input and voice button
            col1, col2 = st.columns([9, 1])
            
            with col2:
                # Initialize recording state
                if 'is_recording' not in st.session_state:
                    st.session_state.is_recording = False
                    st.session_state.audio_recorder_key = 0
                
                # Voice button with different style based on recording state
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
                                    # Process voice input
                                    # [Voice processing code...]
                                    st.rerun()
                    except Exception as e:
                        st.error(f"Error with audio recording: {str(e)}")
            
            with col1:
                prompt = st.chat_input("What would you like help with?")
                
                if prompt:
                    # Add user message to chat history
                    st.session_state.messages.append({"role": "user", "content": prompt, "feedback": None})
                    if st.session_state.get('current_session_id'):
                        save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
                    
                    # Process user query
                    process_user_query(prompt)
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Hidden button to capture session popup toggle state
        if st.button("Toggle Session Manager", key="session_popup_toggle_btn", help="Toggle session manager popup"):
            st.session_state.session_popup_open = not st.session_state.session_popup_open
            st.rerun()
            
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Session manager popup
    popup_class = "session-popup" if st.session_state.session_popup_open else "session-popup hidden"
    
    st.markdown(f'''
    <div class="{popup_class}" id="sessionPopup">
        <div class="popup-header">
            <h3 class="popup-title">💬 Chat History</h3>
            <div class="popup-close" onclick="toggleSessionPopup()">✕</div>
        </div>
        <div id="sessionContent">
            <!-- Session content will be displayed here -->
        </div>
    </div>
    
    <script>
    function toggleSessionPopup() {{
        // This function toggles the session popup visibility
        // We need to trigger a hidden Streamlit button to update the state
        document.querySelector('button[data-testid="baseButton-secondary"]').click();
    }}
    
    </script>
    ''', unsafe_allow_html=True)
    
    # Only render session content when popup is open to save resources
    if st.session_state.session_popup_open:
        # Get user's chat sessions
        sessions_result = get_user_chat_sessions(user_id)
        
        # Use a container to hold the session content
        session_container = st.container()
        
        with session_container:
            # New Chat button
            if st.button("➕ New Chat", key="new_chat", use_container_width=True):
                result = create_chat_session(user_id)
                if result["status"] == "success":
                    st.session_state['current_session_id'] = result["session_id"]
                    st.session_state['messages'] = [{
                        "role": "assistant", 
                        "content": "Hi! I'm ASHA, your career assistant powered by AI. How can I help you today?", 
                        "feedback": None
                    }]
                    # Update URL
                    current_params = dict(st.query_params)
                    current_params['session_id'] = result["session_id"]
                    st.query_params.update(current_params)
                    st.rerun()
            
            st.markdown("<div class='session-list'>", unsafe_allow_html=True)
            
            if sessions_result["status"] == "success":
                sessions = sessions_result["sessions"]
                
                if not sessions:
                    st.markdown("*No chat history yet*")
                else:
                    for session in sessions:
                        session_id = str(session["_id"])
                        title = session.get("title", "New Chat")
                        updated_at = session.get("updated_at", datetime.now())
                        messages = session.get("messages", [])
                        
                        # Get preview text from last user message
                        preview_text = "New conversation"
                        if messages:
                            for msg in reversed(messages):
                                if msg.get("role") == "user":
                                    preview_text = msg.get("content", "")[:50] + "..." if len(msg.get("content", "")) > 50 else msg.get("content", "")
                                    break
                        
                        is_current = session_id == current_session_id
                        
                        # Create session item container
                        st.markdown("<div class='session-item'>", unsafe_allow_html=True)
                        
                        # Session click area
                        if st.button(
                            f"{'🟢 ' if is_current else ''}{title}",
                            key=f"session_click_{session_id}",
                            use_container_width=True,
                            type="primary" if is_current else "secondary"
                        ):
                            st.session_state['current_session_id'] = session_id
                            # Load session messages
                            session_data = get_chat_session(session_id)
                            if session_data["status"] == "success":
                                st.session_state['messages'] = session_data["session"]["messages"]
                            else:
                                st.session_state['messages'] = [{
                                    "role": "assistant", 
                                    "content": "Hi! I'm ASHA, your career assistant powered by AI. How can I help you today?", 
                                    "feedback": None
                                }]
                            # Update URL
                            current_params = dict(st.query_params)
                            current_params['session_id'] = session_id
                            st.query_params.update(current_params)
                            st.rerun()
                        
                        # Preview and date
                        st.markdown(f"<div class='session-preview'>{preview_text}</div>", unsafe_allow_html=True)
                        if isinstance(updated_at, datetime):
                            date_str = updated_at.strftime("%m/%d %H:%M")
                        else:
                            date_str = "Recent"
                        st.markdown(f"<div class='session-date'>{date_str}</div>", unsafe_allow_html=True)
                        
                        # Action buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✏️", key=f"edit_{session_id}", help="Edit title"):
                                st.session_state[f'editing_{session_id}'] = True
                                st.rerun()
                        with col2:
                            if st.button("🗑️", key=f"delete_{session_id}", help="Delete chat"):
                                st.session_state[f'confirm_delete_{session_id}'] = True
                                st.rerun()
                        
                        # Show confirmation for delete
                        if st.session_state.get(f'confirm_delete_{session_id}'):
                            st.warning(f"Delete '{title}'?")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Yes", key=f"confirm_yes_{session_id}"):
                                    result = delete_chat_session(session_id, user_id)
                                    if result["status"] == "success":
                                        # If deleted session was current, create new one
                                        if session_id == current_session_id:
                                            new_result = create_chat_session(user_id)
                                            if new_result["status"] == "success":
                                                st.session_state['current_session_id'] = new_result["session_id"]
                                                st.session_state['messages'] = [{
                                                    "role": "assistant", 
                                                    "content": "Hi! I'm ASHA, your career assistant powered by AI. How can I help you today?", 
                                                    "feedback": None
                                                }]
                                        st.session_state[f'confirm_delete_{session_id}'] = False
                                        st.rerun()
                            with col2:
                                if st.button("No", key=f"confirm_no_{session_id}"):
                                    st.session_state[f'confirm_delete_{session_id}'] = False
                                    st.rerun()
                        
                        # Show edit title input
                        if st.session_state.get(f'editing_{session_id}'):
                            new_title = st.text_input(
                                "New title:", 
                                value=title, 
                                key=f"title_input_{session_id}"
                            )
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Save", key=f"save_{session_id}"):
                                    update_session_title(session_id, user_id, new_title)
                                    st.session_state[f'editing_{session_id}'] = False
                                    st.rerun()
                            with col2:
                                if st.button("Cancel", key=f"cancel_{session_id}"):
                                    st.session_state[f'editing_{session_id}'] = False
                                    st.rerun()
                        
                        st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)