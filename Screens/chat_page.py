
import streamlit as st
import requests
import traceback
import logging
from datetime import datetime
from st_audiorec import st_audiorec
from backend.database import save_chat_history, get_chat_history, sanitize_response
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
            if st.session_state.get('user_id'):
                save_chat_history(st.session_state['user_id'], st.session_state.messages)
                        
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
                if st.session_state.get('user_id'):
                    save_chat_history(st.session_state['user_id'], st.session_state.messages)
                        
                
            except Exception as e:
                error_msg = f"I'm sorry, I encountered an error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg, "feedback": None})
                if st.session_state.get('user_id'):
                    save_chat_history(st.session_state['user_id'], st.session_state.messages)
                        
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

    user_id = st.session_state.get('user_id')

    # Initialize chat history if it doesn't exist
    if 'messages' not in st.session_state:
        # Try to load chat history from MongoDB
        if user_id:
            chat_history = get_chat_history(user_id)
            if chat_history["status"] == "success" and chat_history["messages"]:
                st.session_state.messages = chat_history["messages"]
            else:
                # Default welcome message if no chat history found
                st.session_state.messages = [
                    {"role": "assistant", "content": "Hi! I'm ASHA, your career assistant powered by AI. How can I help you today?", "feedback": None}
                ]
        else:
            # Default welcome message if no user_id
            st.session_state.messages = [
                {"role": "assistant", "content": "Hi! I'm ASHA, your career assistant powered by AI. How can I help you today?", "feedback": None}
            ]

    # Set up the page structure with fixed height containers
    st.markdown("""
    <style>
    .main .block-container {
        padding-bottom: 0rem;
        padding-top: 1rem;
        max-width: 100%;
    }
    
    #chat-container {
        height: calc(100vh - 220px);
        overflow-y: auto;
        padding-right: 1rem;
        margin-bottom: 70px; /* Space for input container */
    }
    
    .stChatInputContainer {
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
        background-color: white !important;
        padding: 1rem 1rem !important;
        z-index: 999 !important;
        box-shadow: 0px -4px 10px rgba(0, 0, 0, 0.1) !important;
    }
    
    .input-container {
        display: flex;
        align-items: center;
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        padding: 10px;
        background-color: white;
        z-index: 1000;
        border-top: 1px solid #ccc;
    }
    
    /* For quick actions */
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
    .stAudioRecorderWrapper {
        display: none !important;
    }
    .custom-recording-indicator {
        color: red;
        font-weight: bold;
        margin-top: 5px;
    }
    </style>
    
    <!-- Auto-scroll JavaScript for the chat container -->
    <script>
    // Function to scroll to the bottom of the chat container
    function scrollToBottom() {
        const chatContainer = document.getElementById('chat-container');
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }
    
    // Set a small delay to ensure content is rendered before scrolling
    setTimeout(scrollToBottom, 100);
    </script>
    """, unsafe_allow_html=True)
    
    # Display quick action buttons above chat messages
    st.markdown('<div class="quick-actions">', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔍 Find Latest Job Postings", key="find_jobs"):
            with st.spinner("Searching for jobs..."):
                try:
                    assistant = st.session_state.get('assistant')
                    response = assistant._get_job_recommendations()
                    st.session_state.messages.append({"role": "user", "content": "Find me latest job postings for you"})
                    st.session_state.messages.append({"role": "assistant", "content": response, "feedback": None})
                    if st.session_state.get('user_id'):
                        save_chat_history(st.session_state['user_id'], st.session_state.messages)
                    
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
                    
                    if st.session_state.get('user_id'):
                        save_chat_history(st.session_state['user_id'], st.session_state.messages)
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
                    
                    if st.session_state.get('user_id'):
                        save_chat_history(st.session_state['user_id'], st.session_state.messages)
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
                    
                    if st.session_state.get('user_id'):
                        save_chat_history(st.session_state['user_id'], st.session_state.messages)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error finding Workshops and sessions: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Create a scrollable container for chat messages with a fixed ID for JavaScript scrolling
    chat_container = st.container()
    st.markdown('<div id="chat-container">', unsafe_allow_html=True)
    
    with chat_container:
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
                                # Save chat history
                                save_result = save_chat_history(st.session_state['user_id'], st.session_state.messages)
                                if save_result["status"] == "error":
                                    # Log the error but don't stop the app
                                    print(f"Warning: Failed to save chat history: {save_result['message']}")
                            except Exception as e:
                                # Log error but allow the chat to continue working
                                print(f"Error saving chat history: {str(e)}") 
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
                            if st.session_state.get('user_id'):
                                save_chat_history(st.session_state['user_id'], st.session_state.messages)
                            st.rerun()
    
    # Add an invisible anchor to scroll to
    st.markdown("<div id='bottom-chat-anchor'></div>", unsafe_allow_html=True)

    # Inject JavaScript to scroll to the anchor on page load
    scroll_script = """
    <script>
        const anchor = document.getElementById("bottom-chat-anchor");
        if (anchor) {
            anchor.scrollIntoView({ behavior: "smooth", block: "end" });
        }
    </script>
    """
    st.markdown(scroll_script, unsafe_allow_html=True)
    
    # Close the chat container div
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Fixed input bar at bottom
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    
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
                            if st.session_state.get('user_id'):
                                save_chat_history(st.session_state['user_id'], st.session_state.messages)
                            
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
                                    if st.session_state.get('user_id'):
                                        save_chat_history(st.session_state['user_id'], st.session_state.messages)
                                    st.rerun()
                                except Exception as e:
                                    error_msg = f"I'm sorry, I encountered an error: {str(e)}"
                                    st.session_state.messages.append({
                                        "role": "assistant", 
                                        "content": error_msg,
                                        "feedback": None
                                    })
                                    if st.session_state.get('user_id'):
                                        save_chat_history(st.session_state['user_id'], st.session_state.messages)
                                    st.rerun()
            except Exception as e:
                st.error(f"Error with audio recording: {str(e)}")
    
    with col1:
        prompt = st.chat_input("What would you like help with?")
        
        if prompt:
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            if st.session_state.get('user_id'):
                save_chat_history(st.session_state['user_id'], st.session_state.messages)
            
            # Check if user is set
            if not st.session_state.get('user_id'):
                content = "It seems you're not logged in. Please log in first so I can provide personalized assistance."
                st.session_state.messages.append({"role": "assistant", "content": content, "feedback": None})
                if st.session_state.get('user_id'):
                    save_chat_history(st.session_state['user_id'], st.session_state.messages)
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

                    if st.session_state.get('user_id'):
                        save_chat_history(st.session_state['user_id'], st.session_state.messages)
                    st.rerun()
                    
                except Exception as e:
                    error_msg = f"I'm sorry, I encountered an error: {str(e)}"
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": error_msg,
                        "feedback": None
                    })

                    if st.session_state.get('user_id'):
                        save_chat_history(st.session_state['user_id'], st.session_state.messages)

                    logger.error(f"Error generating response: {str(e)}")
                    logger.error(traceback.format_exc())
                    st.rerun()
                    
    st.markdown('</div>', unsafe_allow_html=True)