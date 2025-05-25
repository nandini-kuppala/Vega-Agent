import streamlit as st
import os
import json
import requests
from datetime import datetime
import traceback
from crewai import Agent, Task, Crew, Process
import google.generativeai as genai
from langchain_community.chat_models import ChatLiteLLM
import re
from urllib.parse import urlparse
import base64
from io import BytesIO
from PIL import Image
import time
from Screens.chat_page import transcribe_audio, detect_language, translate_text

from st_audiorec import st_audiorec
from Screens.linkedin_repost import scrape_linkedin_post

GEMINI_API_KEY =st.secrets["GEMINI_API_KEY"]

def create_post_generation_agent():
    """Create AI agent for generating social media posts"""
    llm = ChatLiteLLM(
        model="gemini/gemini-1.5-flash",
        api_key=GEMINI_API_KEY,
        temperature=0.7
    )
    
    return Agent(
        role="Social Media Content Creator for Women's Empowerment",
        goal="Create engaging, professional, and empowering social media posts that celebrate women's achievements and promote career growth",
        backstory="""You are an expert social media content creator specializing in women's empowerment and professional networking. 
        You create engaging LinkedIn-style posts that are inspiring, professional, and authentic. You understand the importance of 
        storytelling, using relevant emojis, hashtags, and maintaining a positive, empowering tone. You always ensure content 
        is appropriate, non-controversial, and aligned with professional standards.""",
        verbose=True,
        llm=llm
    )

def create_content_moderation_agent():
    """Create AI agent for content moderation and guardrails"""
    llm = ChatLiteLLM(
        model="gemini/gemini-1.5-flash",
        api_key=GEMINI_API_KEY,
        temperature=0.1
    )
    
    return Agent(
        role="Content Moderation Specialist",
        goal="Ensure all content is appropriate, non-controversial, and aligned with professional standards",
        backstory="""You are a content moderation expert who reviews social media posts for appropriateness. 
        You flag content that might be misleading, controversial, offensive, or unprofessional. You provide 
        constructive feedback to improve content while maintaining empowerment and positivity.""",
        verbose=True,
        llm=llm
    )

def create_post_generation_task(agent, prompt, post_type="general"):
    """Create task for generating posts"""
    return Task(
        description=f"""
        Based on this user request: "{prompt}"
        
        Create an engaging social media post following these guidelines:
        
        1. **Post Type**: {post_type}
        2. **Content Requirements**:
           - Professional and empowering tone
           - Include relevant emojis (2-4 per post)
           - Add appropriate hashtags (5-8 hashtags)
           - Keep it authentic and engaging
           - Focus on women's empowerment and career growth
        
        3. **Structure**:
           - Start with an engaging hook
           - Include personal touch or story if applicable
           - End with a call-to-action or inspiring message
           - Proper formatting with line breaks
        
        4. **Length**: 150-300 words optimal for LinkedIn
        
        5. **Tone**: Professional, inspiring, authentic, and empowering
        
        Generate a complete post that's ready to publish on LinkedIn or similar platforms.
        """,
        agent=agent,
        expected_output="A well-formatted, engaging social media post with emojis and hashtags"
    )

def create_moderation_task(agent, content):
    """Create task for content moderation"""
    return Task(
        description=f"""
        Review this social media post for appropriateness: "{content}"
        
        Check for:
        1. Controversial or sensitive topics
        2. Misleading information
        3. Unprofessional language
        4. Potentially offensive content
        5. Compliance with professional networking standards
        
        Provide:
        - APPROVED/NEEDS_REVISION status
        - Brief explanation of any issues
        - Suggestions for improvement if needed
        
        Focus on maintaining empowerment while ensuring professionalism.
        """,
        agent=agent,
        expected_output="Moderation result with status and feedback"
    )


def generate_post_with_ai(prompt, post_type="general"):
    """Generate post using AI agents"""
    try:
        # Create agents
        post_agent = create_post_generation_agent()
        moderation_agent = create_content_moderation_agent()
        
        # Generate post
        post_task = create_post_generation_task(post_agent, prompt, post_type)
        post_crew = Crew(
            agents=[post_agent],
            tasks=[post_task],
            verbose=True,
            process=Process.sequential
        )
        
        post_result = post_crew.kickoff()
        generated_post = str(post_result)
        
        # Moderate content
        moderation_task = create_moderation_task(moderation_agent, generated_post)
        moderation_crew = Crew(
            agents=[moderation_agent],
            tasks=[moderation_task],
            verbose=True,
            process=Process.sequential
        )
        
        moderation_result = moderation_crew.kickoff()
        moderation_feedback = str(moderation_result)
        
        return {
            "success": True,
            "post": generated_post,
            "moderation": moderation_feedback,
            "approved": "APPROVED" in moderation_feedback.upper()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "post": "",
            "moderation": "",
            "approved": False
        }

def display_post_creation_page():
    """Display the main post creation interface"""
    
    # Check authentication
    if not st.session_state.get('authenticated', False):
        st.warning("Please sign in first")
        st.session_state['page'] = 'login'
        st.rerun()
        return
    
    # Custom CSS styling
    st.markdown("""
    <style>
    /* Main container styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .main-header p {
        margin: 10px 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    
    /* Quick actions styling */
    .quick-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
        margin: 20px 0;
        padding: 20px;
        background: #f8f9fa;
        border-radius: 12px;
        border: 1px solid #e9ecef;
    }
    
    .quick-action-card {
        flex: 1;
        min-width: 200px;
        padding: 15px;
        background: white;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .quick-action-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        border-color: #667eea;
    }
    
    .quick-action-icon {
        font-size: 2rem;
        margin-bottom: 8px;
    }
    
    .quick-action-title {
        font-weight: 600;
        color: #495057;
        margin-bottom: 5px;
    }
    
    .quick-action-desc {
        font-size: 0.9rem;
        color: #6c757d;
    }
    
    /* Chat interface styling */
    .chat-container {
        max-height: 600px;
        overflow-y: auto;
        padding: 20px;
        background: white;
        border-radius: 12px;
        border: 1px solid #e9ecef;
        margin: 20px 0;
    }
    
    .user-message {
        background: #667eea;
        color: white;
        padding: 12px 16px;
        border-radius: 18px 18px 4px 18px;
        margin: 10px 0;
        margin-left: 60px;
        display: inline-block;
        max-width: 80%;
        float: right;
        clear: both;
    }
    
    .assistant-message {
        background: #f8f9fa;
        color: #495057;
        padding: 12px 16px;
        border-radius: 18px 18px 18px 4px;
        margin: 10px 0;
        margin-right: 60px;
        display: inline-block;
        max-width: 80%;
        float: left;
        clear: both;
        border: 1px solid #e9ecef;
    }
    
    .message-container::after {
        content: "";
        display: table;
        clear: both;
    }
    
    /* Input area styling */
    .input-container {
        position: sticky;
        bottom: 0;
        background: white;
        padding: 20px;
        border-top: 1px solid #e9ecef;
        border-radius: 12px 12px 0 0;
    }
    
    /* Post preview styling */
    .post-preview {
        background: white;
        border: 1px solid #e9ecef;
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .post-header {
        display: flex;
        align-items: center;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 1px solid #e9ecef;
    }
    
    .post-avatar {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: #667eea;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        margin-right: 12px;
    }
    
    .post-author {
        font-weight: 600;
        color: #495057;
    }
    
    .post-time {
        font-size: 0.9rem;
        color: #6c757d;
    }
    
    .post-content {
        line-height: 1.6;
        color: #495057;
        white-space: pre-wrap;
    }
    
    .post-actions {
        display: flex;
        justify-content: space-around;
        margin-top: 15px;
        padding-top: 15px;
        border-top: 1px solid #e9ecef;
    }
    
    .post-action {
        display: flex;
        align-items: center;
        gap: 5px;
        color: #6c757d;
        font-size: 0.9rem;
    }
    
    /* Recording indicator */
    .recording-indicator {
        color: #dc3545;
        font-size: 12px;
        text-align: center;
        margin-top: 5px;
        animation: blink 1s infinite;
    }
    
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.3; }
    }
    
    /* Moderation alert styling */
    .moderation-warning {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 12px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    .moderation-approved {
        background: #d1edff;
        border: 1px solid #74c0fc;
        color: #0c5460;
        padding: 12px;
        border-radius: 8px;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main header
    st.markdown("""
    <div class="main-header">
        <h1>✨ AI Post Creator</h1>
        <p>Create engaging posts with ASHA AI - Your smart content companion</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'post_messages' not in st.session_state:
        st.session_state.post_messages = [
            {
                "role": "assistant",
                "content": "Hi! I'm ASHA, your AI content creator. I can help you write engaging posts for your professional network. Try asking me to create a post about your achievements, share industry insights, or even repost from LinkedIn! 🚀"
            }
        ]
    
    if 'generated_post' not in st.session_state:
        st.session_state.generated_post = ""
    
    if 'post_approved' not in st.session_state:
        st.session_state.post_approved = False
    
    # Quick action buttons
    st.markdown("### 🚀 Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🏆 Achievement Post", key="achievement_post", help="Celebrate your wins!"):
            sample_prompt = "I just won the ASHA AI hackathon! Write a celebration post."
            st.session_state.post_messages.append({"role": "user", "content": sample_prompt})
            with st.spinner("Creating your achievement post..."):
                result = generate_post_with_ai(sample_prompt, "achievement")
                if result["success"]:
                    response = f"🎉 Here's your achievement post:\n\n{result['post']}"
                    if not result["approved"]:
                        response += f"\n\n⚠️ **Moderation Note**: {result['moderation']}"
                    st.session_state.post_messages.append({"role": "assistant", "content": response})
                    st.session_state.generated_post = result['post']
                    st.session_state.post_approved = result['approved']
                else:
                    st.session_state.post_messages.append({"role": "assistant", "content": f"Sorry, I encountered an error: {result['error']}"})
            st.rerun()
    
    with col2:
        if st.button("💡 Industry Insight", key="insight_post", help="Share your expertise"):
            sample_prompt = "Write a post about the importance of women in tech leadership roles"
            st.session_state.post_messages.append({"role": "user", "content": sample_prompt})
            with st.spinner("Creating your insight post..."):
                result = generate_post_with_ai(sample_prompt, "insight")
                if result["success"]:
                    response = f"💡 Here's your industry insight post:\n\n{result['post']}"
                    if not result["approved"]:
                        response += f"\n\n⚠️ **Moderation Note**: {result['moderation']}"
                    st.session_state.post_messages.append({"role": "assistant", "content": response})
                    st.session_state.generated_post = result['post']
                    st.session_state.post_approved = result['approved']
                else:
                    st.session_state.post_messages.append({"role": "assistant", "content": f"Sorry, I encountered an error: {result['error']}"})
            st.rerun()
    
    with col3:
        if st.button("🔄 LinkedIn Repost", key="repost_action", help="Repost from LinkedIn"):
            st.session_state.show_linkedin_input = True
            st.rerun()
    
    with col4:
        if st.button("🎯 Custom Post", key="custom_post", help="Create your own"):
            st.session_state.show_custom_input = True
            st.rerun()
    
    # LinkedIn repost interface
    if st.session_state.get('show_linkedin_input', False):
        st.markdown("### 🔗 Repost from LinkedIn")
        linkedin_url = st.text_input("Paste LinkedIn post URL:", placeholder="https://www.linkedin.com/posts/...")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Extract & Repost", key="extract_repost"):
                if linkedin_url:
                    with st.spinner("Extracting LinkedIn post..."):
                        scraped_data = scrape_linkedin_post(linkedin_url)
                        if scraped_data["success"]:
                            prompt = f"Repost this LinkedIn content with my own perspective: {scraped_data['content']}"
                            result = generate_post_with_ai(prompt, "repost")
                            if result["success"]:
                                response = f"🔄 Here's your repost:\n\n{result['post']}"
                                if not result["approved"]:
                                    response += f"\n\n⚠️ **Moderation Note**: {result['moderation']}"
                                st.session_state.post_messages.append({"role": "user", "content": f"Repost from: {linkedin_url}"})
                                st.session_state.post_messages.append({"role": "assistant", "content": response})
                                st.session_state.generated_post = result['post']
                                st.session_state.post_approved = result['approved']
                            else:
                                st.error(f"Error generating repost: {result['error']}")
                        else:
                            st.error(scraped_data["message"])
                else:
                    st.warning("Please enter a LinkedIn URL")
        
        with col2:
            if st.button("Cancel", key="cancel_linkedin"):
                st.session_state.show_linkedin_input = False
                st.rerun()
    
    # Chat interface
    st.markdown("### 💬 Chat with ASHA AI")
    
    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.post_messages:
            with st.chat_message(message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"):
                st.markdown(message["content"])
    
    # Input area
    input_container = st.container()
    with input_container:
        col1, col2, col3 = st.columns([0.8, 0.1, 0.1])
        
        with col1:
            user_input = st.chat_input("Ask me to create a post... (e.g., 'I got promoted to Senior Developer, write a celebration post')")
        
        with col2:
            # Voice input button
            if 'is_recording_post' not in st.session_state:
                st.session_state.is_recording_post = False
            
            button_text = "🛑" if st.session_state.is_recording_post else "🎤"
            if st.button(button_text, key="voice_post_button", help="Voice input"):
                st.session_state.is_recording_post = not st.session_state.is_recording_post
                st.rerun()
            
            if st.session_state.is_recording_post:
                st.markdown("<div class='recording-indicator'>Recording...</div>", unsafe_allow_html=True)
                
                try:
                    wav_audio_data = st_audiorec()
                    if wav_audio_data is not None:
                        st.session_state.is_recording_post = False
                        with st.spinner("Processing voice input..."):
                            transcribed_text = transcribe_audio(wav_audio_data)
                            if transcribed_text:
                                # Process as if it was typed input
                                user_input = transcribed_text
                                st.rerun()
                except Exception as e:
                    st.error(f"Voice input error: {str(e)}")
        
        with col3:
            # Image upload button
            uploaded_image = st.file_uploader("🖼️", type=['png', 'jpg', 'jpeg'], help="Upload image", label_visibility="collapsed")
            if uploaded_image:
                st.session_state.uploaded_image = uploaded_image
                st.success("Image uploaded!")
        
        # Process user input
        if user_input:
            st.session_state.post_messages.append({"role": "user", "content": user_input})
            
            with st.spinner("Creating your post..."):
                # Detect post type from input
                post_type = "general"
                if any(word in user_input.lower() for word in ["won", "achieved", "promoted", "completed", "finished"]):
                    post_type = "achievement"
                elif any(word in user_input.lower() for word in ["insight", "opinion", "trend", "industry"]):
                    post_type = "insight"
                elif "repost" in user_input.lower() or "share" in user_input.lower():
                    post_type = "repost"
                
                result = generate_post_with_ai(user_input, post_type)
                
                if result["success"]:
                    response = f"✨ Here's your {post_type} post:\n\n{result['post']}"
                    
                    # Add moderation feedback
                    if not result["approved"]:
                        response += f"\n\n⚠️ **Content Review**: {result['moderation']}"
                        response += "\n\nWould you like me to revise this post?"
                    else:
                        response += "\n\n✅ **Content Approved**: Ready to publish!"
                    
                    st.session_state.post_messages.append({"role": "assistant", "content": response})
                    st.session_state.generated_post = result['post']
                    st.session_state.post_approved = result['approved']
                else:
                    error_response = f"I encountered an error while creating your post: {result['error']}\n\nPlease try rephrasing your request or contact support if the issue persists."
                    st.session_state.post_messages.append({"role": "assistant", "content": error_response})
            
            st.rerun()
    
    # Post preview section
    if st.session_state.generated_post:
        st.markdown("### 📋 Post Preview")
        
        # Create LinkedIn-style post preview
        st.markdown(f"""
        <div class="post-preview">
            <div class="post-header">
                <div class="post-avatar">
                    {st.session_state.get('user_name', 'You')[0].upper()}
                </div>
                <div>
                    <div class="post-author">{st.session_state.get('user_name', 'Your Name')}</div>
                    <div class="post-time">Just now</div>
                </div>
            </div>
            <div class="post-content">{st.session_state.generated_post}</div>
            <div class="post-actions">
                <div class="post-action">👍 Like</div>
                <div class="post-action">💬 Comment</div>
                <div class="post-action">🔄 Repost</div>
                <div class="post-action">📤 Send</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Action buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📋 Copy Post", key="copy_post"):
                # Copy to clipboard functionality would require JavaScript
                st.success("Post copied to clipboard! (Feature requires JavaScript integration)")
        
        with col2:
            if st.button("✏️ Edit Post", key="edit_post"):
                st.session_state.show_edit_interface = True
                st.rerun()
        
        with col3:
            if st.button("🔄 Regenerate", key="regenerate_post"):
                if st.session_state.post_messages:
                    last_user_message = None
                    for msg in reversed(st.session_state.post_messages):
                        if msg["role"] == "user":
                            last_user_message = msg["content"]
                            break
                    
                    if last_user_message:
                        with st.spinner("Regenerating post..."):
                            result = generate_post_with_ai(last_user_message + " (create a different version)", "general")
                            if result["success"]:
                                st.session_state.generated_post = result['post']
                                st.session_state.post_approved = result['approved']
                                response = f"🔄 Here's a new version:\n\n{result['post']}"
                                if not result["approved"]:
                                    response += f"\n\n⚠️ **Moderation Note**: {result['moderation']}"
                                st.session_state.post_messages.append({"role": "assistant", "content": response})
                                st.rerun()
        
        with col4:
            if st.session_state.post_approved:
                if st.button("🚀 Publish", key="publish_post"):
                    # Here you would integrate with actual posting API
                    st.success("🎉 Post published successfully! (Integration with Herkey.com required)")
                    # Reset the generated post
                    st.session_state.generated_post = ""
                    st.session_state.post_approved = False
            else:
                st.button("🚀 Publish", key="publish_disabled", disabled=True, help="Post needs approval first")
        
        # Edit interface
        if st.session_state.get('show_edit_interface', False):
            st.markdown("### ✏️ Edit Your Post")
            edited_post = st.text_area("Edit your post:", value=st.session_state.generated_post, height=200)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save Changes", key="save_edited"):
                    # Re-moderate the edited content
                    with st.spinner("Reviewing edited content..."):
                        moderation_agent = create_content_moderation_agent()
                        moderation_task = create_moderation_task(moderation_agent, edited_post)
                        moderation_crew = Crew(
                            agents=[moderation_agent],
                            tasks=[moderation_task],
                            verbose=True,
                            process=Process.sequential
                        )
                        moderation_result = moderation_crew.kickoff()
                        moderation_feedback = str(moderation_result)
                        
                        st.session_state.generated_post = edited_post
                        st.session_state.post_approved = "APPROVED" in moderation_feedback.upper()
                        st.session_state.show_edit_interface = False
                        
                        if st.session_state.post_approved:
                            st.success("✅ Edited post approved!")
                        else:
                            st.warning(f"⚠️ Please review: {moderation_feedback}")
                        st.rerun()
            
            with col2:
                if st.button("❌ Cancel Edit", key="cancel_edit"):
                    st.session_state.show_edit_interface = False
                    st.rerun()

# Main execution
if __name__ == "__main__":
    display_post_creation_page()