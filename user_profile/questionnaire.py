import streamlit as st
import requests
import json
import os
from streamlit_lottie import st_lottie
import time
import streamlit.components.v1 as components
from backend.database import create_profile
def load_lottie_file(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def audio_recorder():
    # Simple audio recorder component
    components.html(
        """
        <style>
        .audio-recorder {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            background-color: #f9f9f9;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin: 20px 0;
        }
        
        .record-button {
            background-color: #935073;
            color: white;
            border: none;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            font-size: 24px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        }
        
        .record-button:hover {
            background-color: #7b4361;
            transform: scale(1.05);
        }
        
        .record-button.recording {
            background-color: #ff4d4d;
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        .status-text {
            margin-top: 15px;
            font-weight: bold;
            color: #555;
        }
        </style>
        
        <div class="audio-recorder">
            <button id="recordButton" class="record-button">🎤</button>
            <div id="statusText" class="status-text">Click to Record</div>
            <audio id="audioPlayback" controls style="display:none; margin-top: 15px; width: 100%;"></audio>
        </div>
        
        <script>
            const recordButton = document.getElementById('recordButton');
            const statusText = document.getElementById('statusText');
            const audioPlayback = document.getElementById('audioPlayback');
            
            let mediaRecorder;
            let audioChunks = [];
            let isRecording = false;
            
            recordButton.addEventListener('click', () => {
                if (isRecording) {
                    stopRecording();
                } else {
                    startRecording();
                }
            });
            
            async function startRecording() {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    
                    mediaRecorder.ondataavailable = (event) => {
                        audioChunks.push(event.data);
                    };
                    
                    mediaRecorder.onstop = () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                        const audioUrl = URL.createObjectURL(audioBlob);
                        audioPlayback.src = audioUrl;
                        audioPlayback.style.display = 'block';
                        
                        // Here you would typically send the audio to your backend
                        // For demo purposes, we're just displaying the recording
                    };
                    
                    mediaRecorder.start();
                    isRecording = true;
                    recordButton.classList.add('recording');
                    statusText.innerText = "Recording... Click to Stop";
                    
                } catch (err) {
                    console.error("Error accessing microphone:", err);
                    statusText.innerText = "Error: " + err.message;
                }
            }
            
            function stopRecording() {
                mediaRecorder.stop();
                isRecording = false;
                recordButton.classList.remove('recording');
                statusText.innerText = "Recording Complete";
                audioChunks = [];
            }
        </script>
        """,
        height=200,
    )

def questionnaire_page():
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        st.warning("Please sign in first")
        st.session_state['page'] = 'login'
        st.rerun()
        return
    
    # Import styles
    from utils.design_utils import inject_global_styles, get_styles
    st.markdown(inject_global_styles(), unsafe_allow_html=True)
    styles = get_styles()
    
    # Initialize questionnaire state if not exists
    if 'questionnaire_step' not in st.session_state:
        st.session_state['questionnaire_step'] = 1
        st.session_state['questionnaire_data'] = {}
    
    # Get current step
    step = st.session_state['questionnaire_step']
    
    # Handle large page styling
    st.markdown("""
    <style>
    .question-container {
        padding: 40px;
        margin: 20px 0;
        border-radius: 10px;
        background-color: #ffffff;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    
    .question-title {
        font-size: 22px;
        font-weight: bold;
        margin-bottom: 20px;
        color: #935073;
    }
    
    .option-button {
        display: block;
        width: 100%;
        padding: 12px 15px;
        margin: 8px 0;
        background-color: #f3f3f3;
        border: 1px solid #ddd;
        border-radius: 6px;
        text-align: left;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .option-button:hover {
        background-color: #e6e6e6;
    }
    
    .option-button.selected {
        background-color: #bfee90;
        border-color: #93c06b;
        font-weight: bold;
    }
    
    .navigation-buttons {
        display: flex;
        justify-content: space-between;
        margin-top: 30px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Questionnaire logic based on step
    if step == 1:
        # Section 1: Education & Skills
        st.markdown("<div class='question-container'>", unsafe_allow_html=True)
        
        # Title with animation
        st.markdown("<h1 class='highlight' style='text-align: center;'>Build Your Profile</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; margin-bottom: 30px;'>Let's get to know you better</p>", unsafe_allow_html=True)
        
        # Load and display Lottie animation
        # Usage
        lottie_path = os.path.join("assets", "animations", "education.json")  # Replace with your actual filename
        lottie_json = load_lottie_file(lottie_path)

        if lottie_json:
            st_lottie(lottie_json, height=300, key="education")
        
        st.markdown("<div class='question-title'>What is your highest qualification?</div>", unsafe_allow_html=True)
        qualification = st.selectbox(
            "",
            ["High School", "Diploma", "Bachelor's Degree", "Master's Degree", "PhD", "Other"],
            key="highest_qualification",
            label_visibility="collapsed"
        )
        
        st.markdown("<div class='question-title'>What are some of your professional skills?</div>", unsafe_allow_html=True)
        st.markdown("<p>Separate multiple skills with commas (e.g., marketing, Java, teaching)</p>", unsafe_allow_html=True)
        skills = st.text_area("", key="skills", label_visibility="collapsed")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Navigation buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        with col3:
            if st.button("Next", key="next_button_1"):
                # Save data
                st.session_state['questionnaire_data']['education'] = qualification
                st.session_state['questionnaire_data']['skills'] = skills.split(", ") if skills else []
                # Move to next step
                st.session_state['questionnaire_step'] = 2
                st.rerun()
    
    elif step == 2:
        # Section 2: Career Background
        st.markdown("<div class='question-container'>", unsafe_allow_html=True)
        
        # Title with animation
        st.markdown("<h1 class='highlight' style='text-align: center;'>Career Background</h1>", unsafe_allow_html=True)
        
        # Load and display Lottie animation
        # Usage
        lottie_path = os.path.join("assets", "animations", "career.json")  # Replace with your actual filename
        lottie_json = load_lottie_file(lottie_path)

        if lottie_json:
            st_lottie(lottie_json, height=300, key="career")
        
        st.markdown("<div class='question-title'>Are you currently working, looking for work, or returning after a career break?</div>", unsafe_allow_html=True)
        career_status = st.radio(
            "",
            ["Currently Working", "Looking for Work", "Returning after Career Break"],
            key="career_status",
            label_visibility="collapsed"
        )
        
        st.markdown("<div class='question-title'>How many years of work experience do you have?</div>", unsafe_allow_html=True)
        experience = st.number_input("", min_value=0, max_value=50, step=1, key="experience", label_visibility="collapsed")
        
        st.markdown("<div class='question-title'>What was your most recent job title and company?</div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            job_title = st.text_input("Job Title", key="job_title")
        with col2:
            company = st.text_input("Company", key="company")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Navigation buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("Previous", key="prev_button_2"):
                st.session_state['questionnaire_step'] = 1
                st.rerun()
        with col3:
            if st.button("Next", key="next_button_2"):
                # Save data
                st.session_state['questionnaire_data']['current_status'] = career_status
                st.session_state['questionnaire_data']['experience_years'] = int(experience)
                st.session_state['questionnaire_data']['last_job'] = {
                    "title": job_title,
                    "company": company
                }
                # Move to next step
                st.session_state['questionnaire_step'] = 3
                st.rerun()
    
    elif step == 3:
        # Section 3: Life Stage Support
        st.markdown("<div class='question-container'>", unsafe_allow_html=True)
        
        # Title with animation
        st.markdown("<h1 class='highlight' style='text-align: center;'>Life Circumstances</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; margin-bottom: 30px;'>Help us understand your situation better</p>", unsafe_allow_html=True)
        
        # Load and display Lottie animation
        lottie_path = os.path.join("assets", "animations", "pregnant.json")  # Replace with your actual filename
        lottie_json = load_lottie_file(lottie_path)

        if lottie_json:
            st_lottie(lottie_json, height=300, key="pregnant")
        
        st.markdown("<div class='question-title'>Are you currently pregnant or on maternity leave?</div>", unsafe_allow_html=True)
        preg_status = st.radio(
            "",
            ["Yes, pregnant", "Yes, on maternity leave", "No", "Prefer not to say"],
            key="preg_status",
            label_visibility="collapsed"
        )
        
        st.markdown("<div class='question-title'>Do you need flexible or remote work due to parenting or caregiving responsibilities?</div>", unsafe_allow_html=True)
        flexible = st.radio(
            "",
            ["Yes", "No", "Maybe"],
            key="flexible_work",
            label_visibility="collapsed"
        )
        
        st.markdown("<div class='question-title'>Which of the following describes your situation?</div>", unsafe_allow_html=True)
        life_situation = st.selectbox(
            "",
            ["Single mother", "Returning after long-term caregiving", "Senior woman professional", "Primary caregiver with other responsibilities", "None of the above", "Prefer not to say"],
            key="life_situation",
            label_visibility="collapsed"
        )
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Navigation buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("Previous", key="prev_button_3"):
                st.session_state['questionnaire_step'] = 2
                st.rerun()
        with col3:
            if st.button("Next", key="next_button_3"):
                # Save data
                st.session_state['questionnaire_data']['life_stage'] = {
                    "pregnancy_status": preg_status,
                    "needs_flexible_work": flexible.lower() == "yes",
                    "situation": life_situation
                }
                # Move to next step
                st.session_state['questionnaire_step'] = 4
                st.rerun()
    
    elif step == 4:
        # Section 4: Career Aspirations
        st.markdown("<div class='question-container'>", unsafe_allow_html=True)
        
        # Title with animation
        st.markdown("<h1 class='highlight' style='text-align: center;'>Career Aspirations</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; margin-bottom: 30px;'>Share your professional goals with us</p>", unsafe_allow_html=True)
        
        # Load and display Lottie animation
        lottie_path = os.path.join("assets", "animations", "work.json")  # Replace with your actual filename
        lottie_json = load_lottie_file(lottie_path)

        if lottie_json:
            st_lottie(lottie_json, height=300, key="work")
        
        st.markdown("<div class='question-title'>What kind of jobs are you interested in?</div>", unsafe_allow_html=True)
        job_type = st.selectbox(
            "",
            ["Remote Work", "Flexible Hours", "Part-Time", "Full-Time", "Freelance/Contract", "Any"],
            key="job_type",
            label_visibility="collapsed"
        )
        
        st.markdown("<div class='question-title'>What roles or domains do you want to work in?</div>", unsafe_allow_html=True)
        st.markdown("<p>Separate multiple roles with commas (e.g., HR, Software, Teaching)</p>", unsafe_allow_html=True)
        roles = st.text_input("", key="roles", label_visibility="collapsed")
        
        st.markdown("<div class='question-title'>What is your short-term career goal?</div>", unsafe_allow_html=True)
        short_goal = st.text_area("", key="short_goal", label_visibility="collapsed", placeholder="E.g., Upskill in digital marketing, rejoin the workforce, etc.")
        
        st.markdown("<div class='question-title'>Do you have a long-term dream or aspiration?</div>", unsafe_allow_html=True)
        long_goal = st.text_area("", key="long_goal", label_visibility="collapsed", placeholder="Optional")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Navigation buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("Previous", key="prev_button_4"):
                st.session_state['questionnaire_step'] = 3
                st.rerun()
        with col3:
            if st.button("Next", key="next_button_4"):
                # Save data
                st.session_state['questionnaire_data']['job_preferences'] = {
                    "type": job_type,
                    "roles": roles.split(", ") if roles else [],
                    "short_term_goal": short_goal,
                    "long_term_goal": long_goal
                }
                # Move to next step
                st.session_state['questionnaire_step'] = 5
                st.rerun()
    
    elif step == 5:
        # Section 5: Location Preferences
        st.markdown("<div class='question-container'>", unsafe_allow_html=True)
        
        # Title with animation
        st.markdown("<h1 class='highlight' style='text-align: center;'>Location Preferences</h1>", unsafe_allow_html=True)
        
        # Load and display Lottie animation
        lottie_path = os.path.join("assets", "animations", "location.json")  # Replace with your actual filename
        lottie_json = load_lottie_file(lottie_path)

        if lottie_json:
            st_lottie(lottie_json, height=300, key="location")
        
        st.markdown("<div class='question-title'>Which city do you currently live in?</div>", unsafe_allow_html=True)
        city = st.text_input("", key="current_city", label_visibility="collapsed")
        
        st.markdown("<div class='question-title'>Would you prefer to work remotely, hybrid, or in-office?</div>", unsafe_allow_html=True)
        work_mode = st.selectbox(
            "",
            ["Remote", "Hybrid", "In-office", "Flexible"],
            key="work_mode",
            label_visibility="collapsed"
        )
        
        st.markdown("<div class='question-title'>Are you open to relocating?</div>", unsafe_allow_html=True)
        relocation = st.radio(
            "",
            ["Yes", "No", "Depends on the opportunity"],
            key="relocation",
            label_visibility="collapsed"
        )
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Navigation buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("Previous", key="prev_button_5"):
                st.session_state['questionnaire_step'] = 4
                st.rerun()
        with col3:
            if st.button("Next", key="next_button_5"):
                # Save data
                st.session_state['questionnaire_data']['location'] = {
                    "city": city,
                    "relocation": relocation.lower() == "yes",
                    "work_mode": work_mode
                }
                # Move to next step
                st.session_state['questionnaire_step'] = 6
                st.rerun()
    
    elif step == 6:
        # Section 6: Community & Mentorship
        st.markdown("<div class='question-container'>", unsafe_allow_html=True)
        
        # Title with animation
        st.markdown("<h1 class='highlight' style='text-align: center;'>Community & Mentorship</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; margin-bottom: 30px;'>Connect with like-minded professionals</p>", unsafe_allow_html=True)
        
        # Load and display Lottie animation
        lottie_path = os.path.join("assets", "animations", "community.json")  # Replace with your actual filename
        lottie_json = load_lottie_file(lottie_path)

        if lottie_json:
            st_lottie(lottie_json, height=300, key="community")
        
        st.markdown("<div class='question-title'>Would you like to be connected to a mentor?</div>", unsafe_allow_html=True)
        mentorship = st.radio(
            "",
            ["Yes", "No", "Maybe later"],
            key="mentorship",
            label_visibility="collapsed"
        )
        
        st.markdown("<div class='question-title'>What kind of mentorship would you find helpful?</div>", unsafe_allow_html=True)
        mentorship_type = st.selectbox(
            "",
            ["Job readiness", "Career advancement", "Skill development", "Confidence building", "Work-life balance", "Not applicable"],
            key="mentorship_type",
            label_visibility="collapsed"
        )
        
        st.markdown("<div class='question-title'>Would you be interested in joining community events, webinars, or support circles?</div>", unsafe_allow_html=True)
        events = st.radio(
            "",
            ["Yes", "No", "Maybe"],
            key="community_events",
            label_visibility="collapsed"
        )
        
        st.markdown("<div class='question-title'>Share your thoughts on community support (optional)</div>", unsafe_allow_html=True)
        st.markdown("<p>Click the microphone to record your response</p>", unsafe_allow_html=True)
        audio_recorder()
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Navigation buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("Previous", key="prev_button_6"):
                st.session_state['questionnaire_step'] = 5
                st.rerun()
        with col3:
            if st.button("Next", key="next_button_6"):
                # Save data
                st.session_state['questionnaire_data']['community'] = {
                    "wants_mentorship": mentorship.lower() == "yes",
                    "mentorship_type": mentorship_type if mentorship.lower() != "no" else None,
                    "join_events": events.lower() == "yes"
                }
                # Move to next step
                st.session_state['questionnaire_step'] = 7
                st.rerun()
    
    elif step == 7:
        # Section 7: Consent & Preferences
        st.markdown("<div class='question-container'>", unsafe_allow_html=True)
        
        # Title with animation
        st.markdown("<h1 class='highlight' style='text-align: center;'>Almost Done!</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; margin-bottom: 30px;'>Just a few final details</p>", unsafe_allow_html=True)
        
        # Load and display Lottie animation
        lottie_path = os.path.join("assets", "animations", "congrats.json")  # Replace with your actual filename
        lottie_json = load_lottie_file(lottie_path)

        if lottie_json:
            st_lottie(lottie_json, height=300, key="congrats")
        
        st.markdown("<div class='question-title'>Do you give consent to use your data to build your profile and personalize your job and mentorship suggestions?</div>", unsafe_allow_html=True)
        consent = st.radio(
            "",
            ["Yes", "No"],
            key="consent",
            label_visibility="collapsed"
        )
        
        st.markdown("<div class='question-title'>Would you prefer communication via:</div>", unsafe_allow_html=True)
        comm_pref = st.selectbox(
            "",
            ["Email", "SMS", "WhatsApp"],
            key="comm_pref",
            label_visibility="collapsed"
        )
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Navigation buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("Previous", key="prev_button_7"):
                st.session_state['questionnaire_step'] = 6
                st.rerun()
        with col3:
            if st.button("Submit", key="submit_button"):
                # Check consent
                if consent.lower() != "yes":
                    st.error("We need your consent to create your profile. Please agree to the terms.")
                else:
                    # Save final data
                    st.session_state['questionnaire_data']['communication_preference'] = comm_pref
                    st.session_state['questionnaire_data']['consent'] = consent.lower() == "yes"
                    
                    # Add user_id to profile data
                    st.session_state['questionnaire_data']['user_id'] = st.session_state['user_id']
                    
                    # Submit profile data directly to MongoDB
                    with st.spinner("Creating your profile..."):
                        try:
                            # Use direct database function instead of API call
                            result = create_profile(st.session_state['questionnaire_data'])
                            
                            if result["status"] == "success":
                                # Show success animation
                                lottie_path = os.path.join("assets", "animations", "good.json")
                                lottie_json = load_lottie_file(lottie_path)

                                if lottie_json:
                                    st_lottie(lottie_json, height=300, key="good")
                                
                                # Show success message
                                st.success("Profile created successfully!")
                                time.sleep(2)
                                
                                # Redirect to dashboard
                                st.session_state['page'] = 'dashboard'
                                st.rerun()
                            else:
                                st.error(f"Error: {result['message']}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                