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
    """Display the resume builder page in Streamlit"""
    
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        st.warning("Please sign in first")
        st.session_state['page'] = 'login'
        st.rerun()
        return
    
    st.title("ATS-Friendly Resume Builder")
    
    # Initialize session state variables if they don't exist
    if 'resume_content' not in st.session_state:
        st.session_state.resume_content = None
    if 'resume_html' not in st.session_state:
        st.session_state.resume_html = None
    
    # Create a two-column layout for the input form and resume preview
    col1, col2 = st.columns([3, 2])
    
    with col1:
        with st.expander("📋 Resume Information", expanded=True):
            st.subheader("Let's build your ATS-friendly resume")
            
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
            
            # Personal Information
            st.markdown("#### Personal Information")
            full_name = st.text_input("Full Name")
            email = st.text_input("Email Address")
            phone = st.text_input("Phone Number")
            linkedin = st.text_input("LinkedIn URL (optional)")
            location = st.text_input("Location", 
                                    value=user_profile.get('location', {}).get('city', '') if user_profile else '')
            
            # Education
            st.markdown("#### Education")
            education = st.text_area("Education Details", 
                                    height=100, 
                                    value=default_education,
                                    help="Enter each education entry with degree, institution, and year")
            
            # Work Experience
            st.markdown("#### Work Experience")
            experience = st.text_area("Work Experience", 
                                     height=150,
                                     value=f"Title: {default_job_title}\nCompany: {default_company}\nDuration: {default_experience}\n\nResponsibilities and achievements:",
                                     help="Enter details about your work experience")
            
            # Skills
            st.markdown("#### Skills")
            skills = st.text_area("Skills", 
                                 height=100,
                                 value=default_skills,
                                 help="Enter your skills, separated by commas")
            
            # Projects
            st.markdown("#### Projects")
            projects = st.text_area("Projects", 
                                  height=150,
                                  help="Enter details about relevant projects")
            
            # Achievements
            st.markdown("#### Achievements")
            achievements = st.text_area("Achievements", 
                                      height=100,
                                      help="Enter notable achievements and awards")
            
            # Job Description
            st.markdown("#### Target Job")
            job_description = st.text_area("Paste the Job Description", 
                                         height=200,
                                         help="Paste the complete job description to tailor your resume")
        
        # Generate Resume Button
        if st.button("Generate ATS-Friendly Resume", type="primary", use_container_width=True):
            if not job_description:
                st.error("Please enter a job description to generate a tailored resume.")
                return
            
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
            
            with st.spinner("Building your ATS-friendly resume... This may take a minute or two."):
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
                    
                    st.success("Resume generated successfully!")
                    
                except Exception as e:
                    st.error(f"Error generating resume: {str(e)}")
    
    with col2:
        st.subheader("Resume Preview")
        
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
                    border: 1px solid #ddd;
                    padding: 20px;
                    border-radius: 5px;
                    background-color: white;
                    font-family: 'Arial', sans-serif;
                    font-size: 0.9em;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    margin-bottom: 20px;
                    overflow-y: auto;
                    max-height: 600px;
                }
                .resume-preview h1 {
                    font-size: 1.4em;
                    margin-bottom: 5px;
                    color: #2c3e50;
                }
                .resume-preview h2 {
                    font-size: 1.2em;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 3px;
                    margin-top: 10px;
                    color: #2c3e50;
                }
                .resume-preview p {
                    margin-bottom: 8px;
                    font-size: 0.85em;
                }
                .resume-preview ul {
                    margin-top: 5px;
                    margin-bottom: 10px;
                    padding-left: 20px;
                }
                .resume-preview li {
                    margin-bottom: 3px;
                    font-size: 0.85em;
                }
                </style>
                <div class="resume-preview">
                """ + display_html + """
                </div>
                """, unsafe_allow_html=True)
            
            # Download options
            st.markdown("#### Download Resume")
            
            # Function to create download links
            def create_download_link(content, filename, format_type):
                if format_type == "markdown":
                    b64 = base64.b64encode(content.encode()).decode()
                    href = f'<a href="data:text/plain;base64,{b64}" download="{filename}.md">Download as Markdown</a>'
                elif format_type == "text":
                    b64 = base64.b64encode(content.encode()).decode()
                    href = f'<a href="data:text/plain;base64,{b64}" download="{filename}.txt">Download as Text</a>'
                elif format_type == "html":
                    # Clean HTML before download
                    clean_content = clean_html_for_preview(content)
                    b64 = base64.b64encode(clean_content.encode()).decode()
                    href = f'<a href="data:text/html;base64,{b64}" download="{filename}.html">Download as HTML</a>'
                elif format_type == "pdf":
                    try:
                        # Create PDF from clean HTML
                        pdf_data = html_to_pdf(st.session_state.resume_html, filename)
                        b64 = base64.b64encode(pdf_data).decode()
                        href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}.pdf">Download as PDF</a>'
                    except Exception as e:
                        st.error(f"Failed to create PDF: {str(e)}")
                        href = '<span style="color:red;">PDF creation failed, please try another format</span>'
                
                return href
            
            # Add a helper function for cleaning HTML
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
            
            # Download buttons
            download_format = st.selectbox("Select format", ["PDF", "HTML", "Markdown", "Text"])
            
            if st.button("Download Resume", type="primary"):
                if download_format == "Markdown":
                    download_link = create_download_link(st.session_state.resume_content, "resume", "markdown")
                elif download_format == "Text":
                    # Convert markdown to plain text
                    plain_text = re.sub(r'[#*_]', '', st.session_state.resume_content)
                    download_link = create_download_link(plain_text, "resume", "text")
                elif download_format == "HTML":
                    download_link = create_download_link(st.session_state.resume_html, "resume", "html")
                else:  # PDF
                    download_link = create_download_link(st.session_state.resume_html, "resume", "pdf")
                    
                st.markdown(download_link, unsafe_allow_html=True)
            
        else:
            st.info("Fill in your details and generate your resume to see a preview here.")
            
            # Show placeholder preview
            st.markdown("""
            <div style="border: 1px dashed #ddd; padding: 20px; border-radius: 5px; text-align: center; color: #888;">
                <i class="fas fa-file-alt" style="font-size: 2em;"></i>
                <p>Your ATS-friendly resume will appear here</p>
            </div>
            """, unsafe_allow_html=True)