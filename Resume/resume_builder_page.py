import streamlit as st
from Resume.resume_builder_agent import ResumeBuilderCrew
import streamlit as st
import json
import base64
import tempfile
import os
import pandas as pd
from resume_builder_agent import ResumeBuilderCrew
import markdown
from bs4 import BeautifulSoup
import re
import pdfkit  # For converting HTML to PDF

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
                    from database import get_profile
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
                    
                    # Save the resume content to session state
                    st.session_state.resume_content = resume_content
                    
                    # Convert markdown to HTML for better display
                    html = markdown.markdown(resume_content)
                    
                    # Add CSS styling to the HTML
                    styled_html = f"""
                    <html>
                    <head>
                        <style>
                            body {{
                                font-family: 'Arial', sans-serif;
                                line-height: 1.6;
                                color: #333;
                                max-width: 800px;
                                margin: 0 auto;
                                padding: 20px;
                            }}
                            h1 {{
                                font-size: 24px;
                                margin-bottom: 5px;
                                color: #2c3e50;
                            }}
                            h2 {{
                                font-size: 20px;
                                color: #3498db;
                                border-bottom: 1px solid #ddd;
                                padding-bottom: 5px;
                                margin-top: 20px;
                            }}
                            h3 {{
                                font-size: 18px;
                                margin-bottom: 5px;
                            }}
                            .contact-info {{
                                margin-bottom: 20px;
                            }}
                            ul {{
                                margin-top: 5px;
                                margin-bottom: 15px;
                            }}
                            li {{
                                margin-bottom: 5px;
                            }}
                        </style>
                    </head>
                    <body>
                        {html}
                    </body>
                    </html>
                    """
                    
                    st.session_state.resume_html = styled_html
                    
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
                # Strip HTML head for display (we only want the body content)
                display_html = st.session_state.resume_html
                if "<body>" in display_html and "</body>" in display_html:
                    body_content = display_html.split("<body>")[1].split("</body>")[0]
                else:
                    body_content = display_html
                    
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
                }
                .resume-preview h1 {
                    font-size: 1.6em;
                    margin-bottom: 5px;
                }
                .resume-preview h2 {
                    font-size: 1.3em;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 5px;
                    margin-top: 15px;
                }
                </style>
                <div class="resume-preview">
                """ + body_content + """
                </div>
                """, unsafe_allow_html=True)
            
            # Download options
            st.markdown("#### Download Resume")
            
            # Function to convert and create download links
            def create_download_link(content, filename, format_type):
                if format_type == "markdown":
                    b64 = base64.b64encode(content.encode()).decode()
                    href = f'<a href="data:text/plain;base64,{b64}" download="{filename}.md">Download as Markdown</a>'
                elif format_type == "text":
                    b64 = base64.b64encode(content.encode()).decode()
                    href = f'<a href="data:text/plain;base64,{b64}" download="{filename}.txt">Download as Text</a>'
                elif format_type == "html":
                    b64 = base64.b64encode(content.encode()).decode()
                    href = f'<a href="data:text/html;base64,{b64}" download="{filename}.html">Download as HTML</a>'
                elif format_type == "pdf":
                    # Create PDF from HTML
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as temp_html:
                            temp_html.write(content.encode('utf-8'))
                            temp_html_path = temp_html.name
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
                            temp_pdf_path = temp_pdf.name
                        
                        # Convert HTML to PDF
                        pdfkit_config = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')
                        pdfkit.from_file(temp_html_path, temp_pdf_path, configuration=pdfkit_config)
                        
                        # Read the PDF and encode it
                        with open(temp_pdf_path, 'rb') as pdf_file:
                            pdf_data = pdf_file.read()
                        
                        # Clean up temp files
                        os.unlink(temp_html_path)
                        os.unlink(temp_pdf_path)
                        
                        b64 = base64.b64encode(pdf_data).decode()
                        href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}.pdf">Download as PDF</a>'
                    except Exception as e:
                        # Fallback method using weasyprint if pdfkit fails
                        try:
                            from weasyprint import HTML
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as temp_html:
                                temp_html.write(content.encode('utf-8'))
                                temp_html_path = temp_html.name
                            
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
                                temp_pdf_path = temp_pdf.name
                            
                            # Convert HTML to PDF using WeasyPrint
                            HTML(filename=temp_html_path).write_pdf(temp_pdf_path)
                            
                            # Read the PDF and encode it
                            with open(temp_pdf_path, 'rb') as pdf_file:
                                pdf_data = pdf_file.read()
                            
                            # Clean up temp files
                            os.unlink(temp_html_path)
                            os.unlink(temp_pdf_path)
                            
                            b64 = base64.b64encode(pdf_data).decode()
                            href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}.pdf">Download as PDF</a>'
                        except Exception as e2:
                            st.error(f"Failed to create PDF: {str(e2)}")
                            href = '<span style="color:red;">PDF creation failed, please try another format</span>'
                
                return href
            
            # Download buttons
            download_format = st.selectbox("Select format", ["PDF", "HTML", "Markdown", "Text"])
            
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