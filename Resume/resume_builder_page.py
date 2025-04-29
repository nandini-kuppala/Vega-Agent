# resume_builder_page
import streamlit as st
from backend.database import get_profile
from Resume.resume_builder_agent import ResumeBuilderCrew
import streamlit as st
import json
import base64
import tempfile
import os
import pandas as pd
import markdown
from bs4 import BeautifulSoup
import re
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListItem, ListFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from html.parser import HTMLParser
import html

class HTMLToReportLabParser(HTMLParser):
    """Parser to convert HTML to ReportLab elements optimized for single-page resumes"""
    
    def __init__(self):
        super().__init__()
        self.styles = getSampleStyleSheet()
        self.custom_styles()
        self.elements = []
        self.list_items = []
        self.in_list = False
        self.in_heading = False
        self.heading_level = 0
        self.current_text = ""
        self.in_style_tag = False
        
    def custom_styles(self):
        """Define custom styles for a compact, single-page resume"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='ResumeTitle',
            parent=self.styles['Title'],
            fontSize=14,  # Reduced from 18
            spaceAfter=6,  # Reduced from 10
            textColor=colors.darkblue
        ))
        
        # Heading styles
        self.styles.add(ParagraphStyle(
            name='ResumeH1',
            parent=self.styles['Heading1'],
            fontSize=12,  # Reduced from 16
            spaceAfter=4,  # Reduced from 8
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='ResumeH2',
            parent=self.styles['Heading2'],
            fontSize=11,  # Reduced from 14
            spaceAfter=3,  # Reduced from 6
            textColor=colors.darkblue
        ))
        
        # Section style - compact
        self.styles.add(ParagraphStyle(
            name='ResumeSection',
            parent=self.styles['Normal'],
            fontSize=9,  # Reduced from 11
            spaceAfter=3,  # Reduced from 6
            leading=12  # Reduced from 14
        ))
        
        # Contact info style
        self.styles.add(ParagraphStyle(
            name='ContactInfo',
            parent=self.styles['Normal'],
            fontSize=9,  # Reduced from 11
            alignment=1,  # Center
            spaceAfter=6  # Reduced from 12
        ))
    
    def handle_starttag(self, tag, attrs):
        # Skip style tags completely
        if tag == 'style':
            self.in_style_tag = True
            return
            
        # Process any accumulated text before handling the new tag
        if self.current_text.strip() and not self.in_style_tag:
            self.handle_text_chunk()
        
        if tag == 'ul' or tag == 'ol':
            self.in_list = True
            self.list_items = []
        elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.in_heading = True
            self.heading_level = int(tag[1])
    
    def handle_endtag(self, tag):
        if tag == 'style':
            self.in_style_tag = False
            self.current_text = ""  # Clear any style content
            return
            
        # Process any accumulated text before closing the tag
        if self.current_text.strip() and not self.in_style_tag:
            self.handle_text_chunk()
            
        if tag == 'ul' or tag == 'ol':
            self.in_list = False
            if self.list_items:
                bullet_list = ListFlowable(
                    self.list_items,
                    bulletType='bullet',
                    start=None,
                    bulletFontSize=8,  # Reduced from 10
                    leftIndent=15,     # Reduced from 20
                    bulletOffsetY=0
                )
                self.elements.append(bullet_list)
                self.elements.append(Spacer(1, 0.05*inch))  # Reduced from 0.1*inch
                self.list_items = []
        elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.in_heading = False
            self.heading_level = 0
        elif tag == 'p':
            # Add minimal spacing after paragraphs
            self.elements.append(Spacer(1, 0.05*inch))  # Reduced from 0.1*inch
    
    def handle_data(self, data):
        if not self.in_style_tag:
            # Accumulate text content
            self.current_text += data
    
    def handle_text_chunk(self):
        """Process accumulated text based on current context"""
        text = self.current_text.strip()
        self.current_text = ""
        
        if not text:
            return
            
        if self.in_heading:
            if self.heading_level == 1:
                self.elements.append(Paragraph(text, self.styles['ResumeTitle']))
            elif self.heading_level == 2:
                self.elements.append(Paragraph(text, self.styles['ResumeH1']))
            else:
                self.elements.append(Paragraph(text, self.styles['ResumeH2']))
            self.elements.append(Spacer(1, 0.05*inch))  # Reduced from 0.1*inch
        elif self.in_list:
            list_item_style = self.styles['ResumeSection']
            self.list_items.append(ListItem(Paragraph(text, list_item_style), leftIndent=15))  # Reduced from 20
        else:
            self.elements.append(Paragraph(text, self.styles['ResumeSection']))
    
    def close(self):
        super().close()
        # Process any remaining text
        if self.current_text.strip() and not self.in_style_tag:
            self.handle_text_chunk()
        return self.elements

# Add these functions after the html_to_pdf function and before display_resume_builder_page

def format_markdown_resume(markdown_content, user_profile):
    """Clean and format markdown resume content to ensure proper rendering"""
    # Remove any front matter or metadata if present
    cleaned_content = re.sub(r'^---\s*\n(.*?)\n---\s*\n', '', markdown_content, flags=re.DOTALL)
    
    # Ensure proper heading levels (# for name, ## for sections)
    lines = cleaned_content.split('\n')
    formatted_lines = []
    
    for i, line in enumerate(lines):
        # Fix name heading if it's not properly formatted
        if i == 0 and not line.startswith('#'):
            if re.match(r'^[\w\s]+$', line.strip()):  # If it looks like a name
                formatted_lines.append(f"# {line.strip()}")
                continue
                
        # Fix section headings if they're not properly formatted
        if line.strip() and not line.startswith('#') and i > 0:
            prev_line = lines[i-1].strip()
            if prev_line == '' and re.match(r'^[A-Z][A-Za-z\s]+:?$', line.strip()):
                formatted_lines.append(f"## {line.strip()}")
                continue
                
        formatted_lines.append(line)
    
    formatted_content = '\n'.join(formatted_lines)
    
    # Ensure there's no "Resume" text in the header
    if 'personal_info' in user_profile and 'name' in user_profile['personal_info']:
        user_name = user_profile['personal_info']['name']
        formatted_content = re.sub(r'^# .*Resume.*$', f"# {user_name}", 
                                  formatted_content, flags=re.MULTILINE)
    
    return formatted_content

def convert_to_clean_html(markdown_content):
    """Convert markdown to clean HTML with proper styling for resumes"""
    # Convert markdown to HTML
    html_content = markdown.markdown(markdown_content)
    
    # Parse with BeautifulSoup for cleaning
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Add minimal, clean styling
    style_tag = soup.new_tag('style')
    style_tag.string = """
    body {
        font-family: 'Arial', 'Helvetica', sans-serif;
        font-size: 10pt;
        line-height: 1.2;
        margin: 0;
        padding: 0;
    }
    h1 {
        font-size: 14pt;
        margin-bottom: 5px;
        color: #2c3e50;
        text-align: center;
    }
    h2 {
        font-size: 12pt;
        margin-top: 10px;
        margin-bottom: 5px;
        color: #2c3e50;
        border-bottom: 1px solid #bdc3c7;
    }
    p {
        margin: 3px 0;
    }
    ul {
        margin: 5px 0;
        padding-left: 20px;
    }
    li {
        margin-bottom: 2px;
    }
    .contact-info {
        text-align: center;
        font-size: 9pt;
        margin-bottom: 10px;
    }
    """
    
    # Insert style at the beginning of the document
    if soup.head:
        soup.head.append(style_tag)
    else:
        head_tag = soup.new_tag('head')
        head_tag.append(style_tag)
        soup.insert(0, head_tag)
    
    # Add contact info styling
    contact_paragraphs = soup.find_all('p', limit=2)  # Assume first paragraphs might be contact info
    for p in contact_paragraphs:
        if '@' in p.text or 'Phone' in p.text or 'LinkedIn' in p.text:
            p['class'] = 'contact-info'
    
    return str(soup)

def clean_html_for_preview(html_content):
    """Clean HTML to remove unwanted elements for preview"""
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove style tags
    for style_tag in soup.find_all('style'):
        style_tag.decompose()
    
    # Remove any HTML/head/meta tags
    if soup.head:
        soup.head.decompose()
    
    # If there's an unwanted title that contains "- Resume body" text, remove it
    for tag in soup.find_all(string=re.compile("- Resume body")):
        parent = tag.parent
        if parent:
            parent.decompose()
    
    # Convert back to string
    return str(soup)

def html_to_pdf(html_content, filename):
    """Convert HTML content to PDF using ReportLab with single-page optimization"""
    buffer = BytesIO()
    
    # Set page size to letter with narrower margins to fit more content
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=0.5*inch,  # Reduced from 72pt (1 inch)
        leftMargin=0.5*inch,   # Reduced from 72pt (1 inch)
        topMargin=0.4*inch,    # Reduced from 36pt (0.5 inch) 
        bottomMargin=0.4*inch  # Reduced from 36pt (0.5 inch)
    )
    
    # Clean HTML before parsing - remove any style tags and unwanted headers
    cleaned_html = clean_html_for_pdf(html_content)
    
    # Parse HTML content
    parser = HTMLToReportLabParser()
    parser.feed(cleaned_html)
    elements = parser.close()
    
    # Build PDF
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data

def clean_html_for_pdf(html_content):
    """Clean HTML to remove unwanted elements before PDF conversion"""
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove style tags
    for style_tag in soup.find_all('style'):
        style_tag.decompose()
    
    # Remove any HTML/head/meta tags
    if soup.head:
        soup.head.decompose()
    
    # If there's an unwanted title that contains "- Resume body" text, remove it
    for tag in soup.find_all(string=re.compile("- Resume body")):
        parent = tag.parent
        if parent:
            parent.decompose()
    
    # Convert back to string
    return str(soup)


def display_resume_builder_page():
    """Display the resume builder page in Streamlit with improved UI"""
    
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        st.warning("Please sign in first")
        st.session_state['page'] = 'login'
        st.rerun()
        return
    
    
    # Add custom CSS for overall page styling
    st.markdown("""
    <style>
        .main {
            background-color: #f8f9fa;
            padding: 1.5rem;
        }
        .stApp {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #2c3e50;
            font-weight: 600;
        }
        .css-18e3th9 {
            padding-top: 2rem;
        }
        .block-container {
            padding-top: 1rem;
            padding-bottom: 3rem;
        }
        .stButton>button {
            border-radius: 6px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .stTextInput>div>div>input {
            border-radius: 4px;
        }
        .stTextArea>div>div>textarea {
            border-radius: 4px;
        }
        /* Card styling */
        .card {
            border-radius: 8px;
            background-color: white;
            box-shadow: 0 2px 12px rgba(0,0,0,0.1);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }
        /* Section headers */
        .section-header {
            border-bottom: 2px solid #f0f2f5;
            padding-bottom: 8px;
            margin-bottom: 16px;
            font-size: 1.2rem;
            color: #3498db;
        }
        /* Form field styling */
        .form-field {
            margin-bottom: 10px;
        }
        /* Badges for form sections */
        .section-badge {
            background-color: #e9f5fd;
            color: #3498db;
            font-size: 0.8rem;
            padding: 3px 8px;
            border-radius: 12px;
            margin-right: 8px;
        }
        /* Progress indicator */
        .progress-indicator {
            padding: 8px 0;
            margin-bottom: 16px;
            text-align: center;
        }
        .progress-step {
            display: inline-block;
            margin: 0 12px;
            font-size: 0.85rem;
            color: #7f8c8d;
        }
        .progress-step.active {
            font-weight: bold;
            color: #3498db;
        }
        /* Improve expanders */
        .st-expander {
            border: none !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            margin-bottom: 1rem;
            border-radius: 8px;
        }
        .st-expander-content {
            border-top: 1px solid #f0f2f5;
            padding-top: 10px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Professional header with logo and title
    col_logo, col_title, col_user = st.columns([1, 4, 1])
    with col_logo:
        st.markdown("""
            <div style="text-align: right; padding: 10px;">
                <span style="font-size: 24px; color: #3498db;">
                    <i class="fas fa-file-alt"></i>
                </span>
            </div>
        """, unsafe_allow_html=True)
    
    with col_title:
        st.markdown("""
            <h1 style="text-align: center; margin-bottom: 5px; color: #2c3e50; font-weight: 600;">
                ATS-Friendly Resume Builder
            </h1>
            <p style="text-align: center; color: #7f8c8d; margin-top: 0; font-size: 1rem;">
                Create a professional resume tailored for Applicant Tracking Systems
            </p>
        """, unsafe_allow_html=True)
    
    with col_user:
        if 'user_id' in st.session_state:
            st.markdown(f"""
                <div style="text-align: right; padding: 10px;">
                    <span style="background-color: #e9f5fd; color: #3498db; padding: 5px 10px; border-radius: 20px; font-size: 0.8rem;">
                        <i class="fas fa-user"></i> {st.session_state.get('username', 'User')}
                    </span>
                </div>
            """, unsafe_allow_html=True)
    
    # Add a subtle divider
    st.markdown('<hr style="height: 1px; border: none; background-color: #e0e0e0; margin: 1rem 0;">', unsafe_allow_html=True)
    
    # Initialize session state variables if they don't exist
    if 'resume_content' not in st.session_state:
        st.session_state.resume_content = None
    if 'resume_html' not in st.session_state:
        st.session_state.resume_html = None
    if 'form_step' not in st.session_state:
        st.session_state.form_step = 1
    
    # Progress indicator
    st.markdown("""
        <div class="progress-indicator">
            <div class="progress-step active">1. Enter Information</div>
            <div class="progress-step">→</div>
            <div class="progress-step">2. Generate Resume</div>
            <div class="progress-step">→</div>
            <div class="progress-step">3. Review & Download</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Create a two-column layout for the input form and resume preview
    col1, col2 = st.columns([5, 4])
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("""
            <div style="display: flex; align-items: center; margin-bottom: 20px;">
                <span style="background-color: #3498db; color: white; border-radius: 50%; width: 28px; height: 28px; 
                display: flex; align-items: center; justify-content: center; margin-right: 12px;">
                    <span style="font-size: 0.85rem; font-weight: bold;">1</span>
                </span>
                <h3 style="margin: 0; color: #2c3e50;">Resume Information</h3>
            </div>
        """, unsafe_allow_html=True)
        
        # Get user profile information if available
        user_profile = None
        if 'user_id' in st.session_state:
            try:
                result = get_profile(st.session_state['user_id'])
                if result["status"] == "success":
                    user_profile = result["profile"]
            except Exception as e:
                st.error(f"Error retrieving profile: {str(e)}")
        
        # Pre-fill form fields if we have user profile data
        default_education = user_profile.get('education', '') if user_profile else ''
        default_skills = ', '.join(user_profile.get('skills', [])) if user_profile else ''
        default_experience = f"{user_profile.get('experience_years', '')} years" if user_profile else ''
        default_job_title = user_profile.get('last_job', {}).get('title', '') if user_profile else ''
        default_company = user_profile.get('last_job', {}).get('company', '') if user_profile else ''
        
        # Use tabs for better organization of form sections
        tabs = st.tabs(["📋 Personal", "🎓 Education", "💼 Experience", "🔧 Skills", "🚀 Projects", "🏆 Achievements", "🎯 Target Job"])
        
        with tabs[0]:
            st.markdown('<div class="section-header">Personal Information</div>', unsafe_allow_html=True)
            
            # Two-column layout for personal info
            col_personal_1, col_personal_2 = st.columns(2)
            
            with col_personal_1:
                full_name = st.text_input("Full Name", placeholder="John Doe")
                email = st.text_input("Email Address", placeholder="johndoe@example.com")
                phone = st.text_input("Phone Number", placeholder="(123) 456-7890")
            
            with col_personal_2:
                linkedin = st.text_input("LinkedIn URL", placeholder="linkedin.com/in/johndoe")
                location = st.text_input("Location", 
                                      value=user_profile.get('location', {}).get('city', '') if user_profile else '',
                                      placeholder="City, State, Country")
        
        with tabs[1]:
            st.markdown('<div class="section-header">Education Details</div>', unsafe_allow_html=True)
            st.info("Include degree name, institution, location, and graduation year")
            education = st.text_area("Education", 
                                  height=150, 
                                  value=default_education,
                                  placeholder="Bachelor of Science in Computer Science\nUniversity of California, Berkeley\n2018-2022")
        
        with tabs[2]:
            st.markdown('<div class="section-header">Work Experience</div>', unsafe_allow_html=True)
            st.info("List your work history in reverse chronological order")
            experience = st.text_area("Work Experience", 
                                   height=200,
                                   value=f"Title: {default_job_title}\nCompany: {default_company}\nDuration: {default_experience}\n\nResponsibilities and achievements:",
                                   placeholder="Title: Software Engineer\nCompany: Tech Solutions Inc.\nDuration: 2022-Present\n\nResponsibilities and achievements:\n- Developed scalable web applications using React and Node.js\n- Improved system performance by 40% through code optimization")
        
        with tabs[3]:
            st.markdown('<div class="section-header">Skills</div>', unsafe_allow_html=True)
            skills = st.text_area("Technical & Professional Skills", 
                               height=120,
                               value=default_skills,
                               placeholder="JavaScript, React, Python, Project Management, Team Leadership")
            
            # Optional skill categorization
            with st.expander("Categorize your skills (optional)"):
                st.markdown("""
                    <div style="font-size: 0.9rem;">
                        Organizing skills by category can make your resume more readable.
                    </div>
                """, unsafe_allow_html=True)
                
                col_skill_1, col_skill_2 = st.columns(2)
                with col_skill_1:
                    technical_skills = st.text_area("Technical Skills", 
                                                 height=100,
                                                 placeholder="Programming languages, tools, etc.")
                with col_skill_2:
                    soft_skills = st.text_area("Soft Skills", 
                                            height=100,
                                            placeholder="Leadership, communication, etc.")
        
        with tabs[4]:
            st.markdown('<div class="section-header">Projects</div>', unsafe_allow_html=True)
            projects = st.text_area("Projects", 
                                 height=150,
                                 placeholder="Project Name: E-commerce Platform\nDuration: 3 months\nTechnologies: React, Node.js, MongoDB\n\nDescription:\n- Built a full-stack e-commerce platform with user authentication\n- Implemented payment processing using Stripe API")
        
        with tabs[5]:
            st.markdown('<div class="section-header">Achievements</div>', unsafe_allow_html=True)
            achievements = st.text_area("Awards & Achievements", 
                                     height=120,
                                     placeholder="- Employee of the Month (June 2023)\n- Increased team productivity by 25% through process improvements\n- Published research paper on AI ethics")
        
        with tabs[6]:
            st.markdown('<div class="section-header">Target Job</div>', unsafe_allow_html=True)
            st.warning("Paste the job description to tailor your resume for better ATS performance")
            job_description = st.text_area("Job Description", 
                                        height=200,
                                        placeholder="Paste the complete job description here...")
        
        # Generate Resume Button (outside tabs, at bottom of form)
        st.markdown('<div style="margin-top: 1.5rem;">', unsafe_allow_html=True)
        generate_col1, generate_col2 = st.columns([3, 1])
        with generate_col1:
            generate_button = st.button("Generate ATS-Friendly Resume", 
                                    type="primary", 
                                    use_container_width=True,
                                    help="Click to generate your tailored resume")
        with generate_col2:
            clear_button = st.button("Clear Form", 
                                  use_container_width=True,
                                  help="Clear all fields and start over")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)  # Close card div
        
        # Handle the generate button click
        if generate_button:
            if not job_description:
                st.error("Please enter a job description to generate a tailored resume.")
            else:
                # Format user data into a profile dictionary
                formatted_user_profile = {
                    "personal_info": {
                        "name": full_name,
                        "email": email,
                        "phone": phone,
                        "linkedin": linkedin,
                        "location": location
                    },
                    "education": education,
                    "experience": experience,
                    "skills": skills.split(",") if skills else []
                }
                
                # Add user profile data if available
                if user_profile:
                    formatted_user_profile.update({
                        "education": user_profile.get('education', education),
                        "experience_years": user_profile.get('experience_years', ''),
                        "last_job": user_profile.get('last_job', {}),
                        "skills": user_profile.get('skills', skills.split(",") if skills else []),
                        "location": user_profile.get('location', {})
                    })
                
                with st.spinner("Building your ATS-friendly resume..."):
                    try:
                        # Create and run the resume builder crew
                        resume_builder = ResumeBuilderCrew(api_key=st.secrets["GEMINI_API_KEY"])
                        resume_content = resume_builder.build_resume(
                            user_profile=formatted_user_profile,
                            job_description=job_description,
                            projects=projects,
                            achievements=achievements
                        )
                        # Apply the formatting helpers:
                        formatted_resume = format_markdown_resume(resume_content, formatted_user_profile)
                        st.session_state.resume_content = formatted_resume

                        # Convert markdown to clean HTML for better display
                        clean_html = convert_to_clean_html(formatted_resume)
                        st.session_state.resume_html = clean_html
                        
                        # Update progress step
                        st.session_state.form_step = 3
                        
                        st.success("Resume generated successfully!")
                        
                    except Exception as e:
                        st.error(f"Error generating resume: {str(e)}")
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        st.markdown("""
            <div style="display: flex; align-items: center; margin-bottom: 20px;">
                <span style="background-color: #3498db; color: white; border-radius: 50%; width: 28px; height: 28px; 
                display: flex; align-items: center; justify-content: center; margin-right: 12px;">
                    <span style="font-size: 0.85rem; font-weight: bold;">2</span>
                </span>
                <h3 style="margin: 0; color: #2c3e50;">Resume Preview</h3>
            </div>
        """, unsafe_allow_html=True)
        
        # Display the resume preview if available
        if st.session_state.resume_html:
            # Create a container with styling for the resume preview
            preview_container = st.container()
            with preview_container:
                # Clean the HTML before displaying it
                display_html = clean_html_for_preview(st.session_state.resume_html)
                
                st.markdown("""
                <style>
                .resume-preview {
                    border: 1px solid #e0e0e0;
                    padding: 25px;
                    border-radius: 8px;
                    background-color: white;
                    font-family: 'Arial', sans-serif;
                    font-size: 0.9em;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                    margin-bottom: 20px;
                    overflow-y: auto;
                    max-height: 600px;
                }
                .resume-preview h1 {
                    font-size: 1.5em;
                    margin-bottom: 8px;
                    color: #2c3e50;
                    text-align: center;
                    padding-bottom: 5px;
                }
                .resume-preview h2 {
                    font-size: 1.2em;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 5px;
                    margin-top: 15px;
                    color: #2c3e50;
                }
                .resume-preview p {
                    margin-bottom: 8px;
                    font-size: 0.9em;
                    line-height: 1.5;
                }
                .resume-preview ul {
                    margin-top: 5px;
                    margin-bottom: 10px;
                    padding-left: 20px;
                }
                .resume-preview li {
                    margin-bottom: 5px;
                    font-size: 0.85em;
                    line-height: 1.4;
                }
                .resume-preview .contact-info {
                    text-align: center;
                    margin-bottom: 15px;
                    color: #555;
                    font-size: 0.85em;
                }
                .resume-preview .section {
                    margin-bottom: 15px;
                }
                .resume-preview .job-title {
                    font-weight: bold;
                    color: #333;
                }
                .resume-preview .company {
                    font-style: italic;
                }
                .resume-preview .date {
                    color: #555;
                    font-size: 0.85em;
                }
                .resume-preview .skills-list {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 8px;
                }
                .resume-preview .skill-item {
                    background-color: #f0f8ff;
                    padding: 3px 8px;
                    border-radius: 12px;
                    font-size: 0.8em;
                    color: #2980b9;
                }
                </style>
                <div class="resume-preview">
                """ + display_html + """
                </div>
                """, unsafe_allow_html=True)
            
            # Download options
            st.markdown('<div class="section-header">Download Options</div>', unsafe_allow_html=True)
            
            # Function to create download links
            def create_download_link(content, filename, format_type):
                if format_type == "markdown":
                    b64 = base64.b64encode(content.encode()).decode()
                    href = f'<a href="data:text/plain;base64,{b64}" download="{filename}.md" class="download-link">Download as Markdown</a>'
                elif format_type == "text":
                    b64 = base64.b64encode(content.encode()).decode()
                    href = f'<a href="data:text/plain;base64,{b64}" download="{filename}.txt" class="download-link">Download as Text</a>'
                elif format_type == "html":
                    # Clean HTML before download
                    clean_content = clean_html_for_preview(content)
                    b64 = base64.b64encode(clean_content.encode()).decode()
                    href = f'<a href="data:text/html;base64,{b64}" download="{filename}.html" class="download-link">Download as HTML</a>'
                elif format_type == "pdf":
                    try:
                        # Create PDF from clean HTML
                        pdf_data = html_to_pdf(st.session_state.resume_html, filename)
                        b64 = base64.b64encode(pdf_data).decode()
                        href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}.pdf" class="download-link">Download as PDF</a>'
                    except Exception as e:
                        st.error(f"Failed to create PDF: {str(e)}")
                        href = '<span style="color:red;">PDF creation failed, please try another format</span>'
                
                return href
            
            
            # Download section with better styling
            st.markdown("""
            <style>
                .download-options {
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }
                .download-row {
                    display: flex;
                    align-items: center;
                    gap: 15px;
                }
                .download-format {
                    background-color: #f8f9fa;
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    padding: 8px 12px;
                    flex: 1;
                    cursor: pointer;
                    text-align: center;
                    transition: all 0.2s ease;
                }
                .download-format:hover {
                    background-color: #e9f5fd;
                    border-color: #3498db;
                }
                .download-format.active {
                    background-color: #e9f5fd;
                    border-color: #3498db;
                    color: #3498db;
                    font-weight: 600;
                }
                .download-link {
                    display: inline-block;
                    background-color: #3498db;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 6px;
                    text-decoration: none;
                    font-weight: 600;
                    margin-top: 10px;
                    text-align: center;
                    transition: background-color 0.2s ease;
                }
                .download-link:hover {
                    background-color: #2980b9;
                }
            </style>
            """, unsafe_allow_html=True)
            
            # Download format selector with better visual feedback
            download_format = st.radio(
                "Select format",
                ["PDF", "HTML", "Markdown", "Text"],
                horizontal=True,
                label_visibility="collapsed"
            )
            
            # Format description based on selection
            format_descriptions = {
                "PDF": "Best for job applications and printing",
                "HTML": "Web-ready format with full formatting",
                "Markdown": "Lightweight and easy to edit further",
                "Text": "Simple plain text format"
            }
            
            st.markdown(f"""
                <div style="background-color: #f0f7fb; border-left: 4px solid #3498db; padding: 10px; margin: 10px 0; font-size: 0.9rem;">
                    <strong>{download_format}</strong>: {format_descriptions[download_format]}
                </div>
            """, unsafe_allow_html=True)
            
            download_col1, download_col2 = st.columns([3, 1])
            with download_col1:
                resume_name = st.text_input("File name", value="my_resume", placeholder="Enter file name")
            
            with download_col2:
                if st.button("Download", type="primary", use_container_width=True):
                    if download_format == "Markdown":
                        download_link = create_download_link(st.session_state.resume_content, resume_name, "markdown")
                    elif download_format == "Text":
                        # Convert markdown to plain text
                        plain_text = re.sub(r'[#*_]', '', st.session_state.resume_content)
                        download_link = create_download_link(plain_text, resume_name, "text")
                    elif download_format == "HTML":
                        download_link = create_download_link(st.session_state.resume_html, resume_name, "html")
                    else:  # PDF
                        download_link = create_download_link(st.session_state.resume_html, resume_name, "pdf")
                        
                    st.markdown(download_link, unsafe_allow_html=True)
            
        else:
            # More visually appealing placeholder preview
            st.markdown("""
            <div style="
                border: 2px dashed #e0e0e0; 
                padding: 40px; 
                border-radius: 8px; 
                text-align: center; 
                color: #7f8c8d;
                background-color: #f9f9f9;
                height: 400px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            ">
                <div style="font-size: 3rem; color: #bdc3c7; margin-bottom: 20px;">
                    <i class="fas fa-file-alt"></i>
                </div>
                <h3 style="margin-bottom: 10px; color: #7f8c8d;">Your Resume Preview</h3>
                <p style="max-width: 300px; margin: 0 auto;">
                    Fill in your details and generate your ATS-friendly resume to see it here
                </p>
                <div style="margin-top: 30px; width: 60%; height: 1px; background-color: #e0e0e0;"></div>
                <div style="margin-top: 30px; font-size: 0.9rem; color: #95a5a6;">
                    <i class="fas fa-info-circle"></i> 
                    Tailored to pass ATS screening and impress recruiters
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)  # Close card div
        
    # Add footer with helpful tips
    st.markdown("""
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 20px; font-size: 0.9rem;">
        <h4 style="margin-top: 0; color: #2c3e50;">Resume Tips</h4>
        <ul style="margin-bottom: 0; padding-left: 20px;">
            <li>Use concrete numbers and achievements where possible (e.g., "Increased sales by 20%")</li>
            <li>Match keywords from the job description to improve ATS ranking</li>
            <li>Focus on relevant experience and skills for the position</li>
            <li>Keep your resume concise and well-organized</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)