
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
    """Display a chat interface with session management in right sidebar"""
    
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        st.warning("Please sign in first")
        st.session_state['page'] = 'login'
        st.rerun()
        return
    
    user_id = st.session_state.get('user_id')
    current_session_id = st.session_state.get('current_session_id')
    
    # Initialize sidebar for chat history
    with st.sidebar:
        st.header("💬 Chat History")
        
        # New Chat button
        if st.button("➕ New Chat", use_container_width=True):
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
                st.subheader("Previous Sessions")
                
                for idx, session in enumerate(sessions):
                    session_id = str(session["_id"])
                    title = session.get("title", "New Chat")
                    updated_at = session.get("updated_at", datetime.now())
                    messages = session.get("messages", [])
                    
                    # Get preview text from last user message
                    preview_text = "New conversation"
                    if messages:
                        for msg in reversed(messages):
                            if msg.get("role") == "user":
                                preview_text = msg.get("content", "")[:40] + "..." if len(msg.get("content", "")) > 40 else msg.get("content", "")
                                break
                    
                    is_current = session_id == current_session_id
                    
                    # Create expandable section for each session
                    with st.expander(f"{'🔸' if is_current else '💭'} {title}", expanded=is_current):
                        st.caption(preview_text)
                        st.caption(f"Last updated: {updated_at.strftime('%m/%d %H:%M') if isinstance(updated_at, datetime) else 'Recent'}")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if not is_current:
                                if st.button("Load", key=f"load_{session_id}"):
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
                            else:
                                st.success("Current")
                        
                        with col2:
                            if st.button("✏️ Edit", key=f"edit_{session_id}"):
                                st.session_state[f'editing_title_{session_id}'] = True
                                st.rerun()
                        
                        with col3:
                            if st.button("🗑️ Delete", key=f"delete_{session_id}"):
                                st.session_state[f'confirm_delete_{session_id}'] = True
                                st.rerun()
                        
                        # Edit title interface
                        if st.session_state.get(f'editing_title_{session_id}'):
                            new_title = st.text_input(
                                "New title:", 
                                value=title, 
                                key=f"title_input_{session_id}",
                                placeholder="Enter new title..."
                            )
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Save", key=f"save_title_{session_id}"):
                                    update_session_title(session_id, user_id, new_title)
                                    st.session_state[f'editing_title_{session_id}'] = False
                                    st.success("Title updated!")
                                    st.rerun()
                            with col2:
                                if st.button("Cancel", key=f"cancel_edit_{session_id}"):
                                    st.session_state[f'editing_title_{session_id}'] = False
                                    st.rerun()
                        
                        # Confirmation dialog for delete
                        if st.session_state.get(f'confirm_delete_{session_id}'):
                            st.warning(f"Are you sure you want to delete '{title}'?")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Yes, Delete", key=f"confirm_yes_{session_id}", type="primary"):
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
                                        st.success("Session deleted!")
                                        st.rerun()
                            with col2:
                                if st.button("Cancel", key=f"cancel_delete_{session_id}"):
                                    st.session_state[f'confirm_delete_{session_id}'] = False
                                    st.rerun()
    
    # Main chat area
    st.title("ASHA AI Chat Bot")
    
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
    
    # Display quick action buttons
    st.subheader("Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔍 Find Latest Job Postings", use_container_width=True):
            with st.spinner("Searching for jobs..."):
                try:
                    assistant = st.session_state.get('assistant')
                    response = assistant._get_job_recommendations()
                    st.session_state.messages.append({"role": "user", "content": "Find me latest job postings", "feedback": None})
                    st.session_state.messages.append({"role": "assistant", "content": response, "feedback": None})
                    if st.session_state.get('current_session_id'):
                        save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error finding jobs: {str(e)}")
    
    with col2:
        if st.button("🎯 Find Upcoming Events", use_container_width=True):
            with st.spinner("Discovering events..."):
                try:
                    assistant = st.session_state.get('assistant')
                    response = assistant._get_event_recommendations()
                    st.session_state.messages.append({"role": "user", "content": "Find upcoming events", "feedback": None})
                    st.session_state.messages.append({"role": "assistant", "content": response, "feedback": None})
                    if st.session_state.get('current_session_id'):
                        save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error finding events: {str(e)}")
    
    with col3:
        if st.button("👥 Find Community Groups", use_container_width=True):
            with st.spinner("Discovering community groups..."):
                try:
                    assistant = st.session_state.get('assistant')
                    response = assistant._get_community_recommendations()
                    st.session_state.messages.append({"role": "user", "content": "Find community groups", "feedback": None})
                    st.session_state.messages.append({"role": "assistant", "content": response, "feedback": None})
                    if st.session_state.get('current_session_id'):
                        save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error finding community groups: {str(e)}")

    with col4:
        if st.button("🧑‍🏫 Find Workshops", use_container_width=True):
            with st.spinner("Discovering sessions..."):
                try:
                    assistant = st.session_state.get('assistant')
                    response = assistant._get_session_recommendations()
                    st.session_state.messages.append({"role": "user", "content": "Find workshops and sessions", "feedback": None})
                    st.session_state.messages.append({"role": "assistant", "content": response, "feedback": None})
                    if st.session_state.get('current_session_id'):
                        save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error finding workshops: {str(e)}")
    
    st.divider()
    
    # Display chat messages with feedback buttons
    chat_container = st.container()
    with chat_container:
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"], avatar="👩‍💼" if message["role"] == "assistant" else None):
                st.markdown(message["content"])
                
                # Add feedback buttons only for assistant messages
                if message["role"] == "assistant" and i > 0:
                    feedback_cols = st.columns([1, 1, 8])
                    
                    # Add feedback status if already provided
                    if message.get("feedback") is not None:
                        if message["feedback"] == "positive":
                            feedback_cols[0].success("👍 Liked")
                        else:
                            feedback_cols[1].error("👎 Disliked")
                    else:
                        # Thumbs up button
                        if feedback_cols[0].button("👍 Like", key=f"thumbs_up_{i}"):
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
                                save_result = save_session_messages(st.session_state['current_session_id'], st.session_state.messages)
                                if save_result["status"] == "error":
                                    print(f"Warning: Failed to save session messages: {save_result['message']}")
                            except Exception as e:
                                print(f"Error saving session messages: {str(e)}")
                            st.rerun()
                        
                        # Thumbs down button
                        if feedback_cols[1].button("👎 Dislike", key=f"thumbs_down_{i}"):
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
    
    # Chat input area
    st.divider()
    
    # Create columns for voice and text input
    input_col1, input_col2 = st.columns([9, 1])
    
    with input_col2:
        # Initialize recording state
        if 'is_recording' not in st.session_state:
            st.session_state.is_recording = False
            st.session_state.audio_recorder_key = 0
        
        # Voice button with different style based on recording state
        button_text = "🛑 Stop" if st.session_state.is_recording else "🎤 Voice"
        button_type = "secondary" if st.session_state.is_recording else "primary"
        
        if st.button(button_text, key="voice_button", help="Toggle voice recording", type=button_type):
            st.session_state.is_recording = not st.session_state.is_recording
            st.session_state.audio_recorder_key += 1
            st.rerun()
        
        # Show recording indicator
        if st.session_state.is_recording:
            st.warning("🔴 Recording...")
        
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
    
    with input_col1:
        # Text input
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