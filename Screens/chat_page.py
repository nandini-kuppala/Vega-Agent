
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
    """Display a chat interface with session management in Streamlit sidebar"""
    
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        st.warning("Please sign in first")
        st.session_state['page'] = 'login'
        st.rerun()
        return
    
    user_id = st.session_state.get('user_id')
    current_session_id = st.session_state.get('current_session_id')
    
    # Add CSS styling for chat interface
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

    /* Fixed input area */
    .fixed-input {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 15px;
        background: white;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
        z-index: 1000;
        border-top: 1px solid #e0e0e0;
    }

    /* Quick actions styling */
    .quick-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 15px;
        padding: 0 10px;
    }

    .quick-action-button {
        background-color: #f5f5f5;
        border: 1px solid #ddd;
        border-radius: 20px;
        padding: 8px 15px;
        font-size: 14px;
        cursor: pointer;
        transition: all 0.3s ease;
        white-space: nowrap;
    }

    .quick-action-button:hover {
        background-color: #e0e0e0;
        border-color: #bbb;
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* Recording indicator */
    .custom-recording-indicator {
        color: red;
        font-size: 12px;
        text-align: center;
        margin-top: 5px;
        animation: blink 1s infinite;
    }

    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.3; }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Streamlit Native Sidebar for Chat History
    with st.sidebar:
        st.markdown("### 💬 Chat History")
        
        # New Chat button
        if st.button("➕ New Chat", key="new_chat_sidebar", help="Start a new conversation"):
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
        
        st.divider()
        
        # Get user's chat sessions
        sessions_result = get_user_chat_sessions(user_id)
        if sessions_result["status"] == "success":
            sessions = sessions_result["sessions"]
            
            if not sessions:
                st.info("No chat history yet")
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
                    
                    # Session container
                    with st.container():
                        # Use different styling for current session
                        if is_current:
                            st.markdown(f"**🔵 {title}**")
                        else:
                            st.markdown(f"**{title}**")
                        
                        # Preview text
                        st.caption(preview_text)
                        
                        # Date
                        date_str = updated_at.strftime("%m/%d %H:%M") if isinstance(updated_at, datetime) else "Recent"
                        st.caption(f"📅 {date_str}")
                        
                        # Action buttons in columns
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if not is_current and st.button("📂", key=f"load_{session_id}", help="Load conversation"):
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
                        
                        with col2:
                            if st.button("✏️", key=f"edit_{session_id}", help="Edit title"):
                                st.session_state[f'editing_{session_id}'] = True
                                st.rerun()
                        
                        with col3:
                            if st.button("🗑️", key=f"delete_{session_id}", help="Delete"):
                                st.session_state[f'confirm_delete_{session_id}'] = True
                                st.rerun()
                        
                        # Edit title interface
                        if st.session_state.get(f'editing_{session_id}'):
                            new_title = st.text_input(
                                "New title:", 
                                value=title, 
                                key=f"title_input_{session_id}"
                            )
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("💾", key=f"save_{session_id}", help="Save"):
                                    update_session_title(session_id, user_id, new_title)
                                    st.session_state[f'editing_{session_id}'] = False
                                    st.rerun()
                            with col2:
                                if st.button("❌", key=f"cancel_{session_id}", help="Cancel"):
                                    st.session_state[f'editing_{session_id}'] = False
                                    st.rerun()
                        
                        # Delete confirmation
                        if st.session_state.get(f'confirm_delete_{session_id}'):
                            st.warning(f"Delete '{title}'?")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Yes", key=f"confirm_yes_{session_id}"):
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
                                if st.button("❌ No", key=f"confirm_no_{session_id}"):
                                    st.session_state[f'confirm_delete_{session_id}'] = False
                                    st.rerun()
                        
                        st.divider()
    
    # Main chat container
    main_container = st.container()

    with main_container:
        # Header
        st.markdown("""
        <div class="header-container">
            <h1>ASHA AI Chat Bot</h1>
        </div>
        """, unsafe_allow_html=True)
        
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
                                
        
        # Create a spacer to ensure content is visible above the fixed input bar
        st.markdown("<div style='padding-bottom: 80px;'></div>", unsafe_allow_html=True)
        
        # Input area
        with input_container:
            
            col1, col2 = st.columns([0.9, 0.1])  # Use integer ratio instead of float
            
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
                                    # Detect language
                                    detected_lang = detect_language(transcribed_text)
                                    st.session_state.detected_language = detected_lang
                                    
                                    # Translate to English if not already in English
                                    if detected_lang != "en-IN":
                                        english_text = translate_text(transcribed_text, detected_lang, "en-IN")
                                    else:
                                        english_text = transcribed_text
                                    
                                    # Add user message to chat history
                                    st.session_state.messages.append({"role": "user", "content": transcribed_text, "feedback": None})
                                    if st.session_state.get('current_session_id'):
                                        save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
                                    
                                    # Generate assistant response
                                    with st.spinner("Generating response..."):
                                        try:
                                            # Process the query using our CareerGuidanceChatbot
                                            assistant = st.session_state.get('assistant')
                                            response = assistant.process_query(english_text)
                                            response = sanitize_response(response)
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
                                            if st.session_state.get('current_session_id'):
                                                save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
                                            st.rerun()
                                        except Exception as e:
                                            error_msg = f"I'm sorry, I encountered an error: {str(e)}"
                                            st.session_state.messages.append({
                                                "role": "assistant", 
                                                "content": error_msg,
                                                "feedback": None
                                            })
                                            if st.session_state.get('current_session_id'):
                                                save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
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
                        
                    
                    # Check if user is set
                    if not st.session_state.get('user_id'):
                        content = "It seems you're not logged in. Please log in first so I can provide personalized assistance."
                        st.session_state.messages.append({"role": "assistant", "content": content, "feedback": None})
                        if st.session_state.get('current_session_id'):
                            save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
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
                            response = sanitize_response(response)
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

                            if st.session_state.get('current_session_id'):
                                save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
                            st.rerun()
                            
                        except Exception as e:
                            error_msg = f"I'm sorry, I encountered an error: {str(e)}"
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": error_msg,
                                "feedback": None
                            })

                            if st.session_state.get('current_session_id'):
                                save_session_messages(st.session_state['current_session_id'], st.session_state.messages)

                            logger.error(f"Error generating response: {str(e)}")
                            logger.error(traceback.format_exc())
                            st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)