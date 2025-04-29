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


import streamlit as st
import json
import os
from datetime import datetime
from Resume.resume_builder_agent import ResumeBuilderCrew
from Resume.latex_formatter import LaTeXResumeFormatter
from Resume.pdf_converter import LaTeXPDFConverter

def display_resume_builder_page():
    """
    Display the resume builder page with form inputs and resume generation functionality
    """
    st.title("AI-Powered Resume Builder")
    st.markdown("### Create an ATS-optimized resume tailored to your target job")
    
    # Initialize session state for form data if it doesn't exist
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = {
            'name': '',
            'email': '',
            'phone': '',
            'linkedin': '',
            'github': '',
            'location': ''
        }
    
    if 'education' not in st.session_state:
        st.session_state.education = [{
            'institution': '',
            'degree': '',
            'year': '',
            'location': '',
            'gpa': ''
        }]
    
    if 'experience' not in st.session_state:
        st.session_state.experience = [{
            'title': '',
            'company': '',
            'duration': '',
            'location': '',
            'responsibilities': ['', '', '']
        }]
    
    if 'projects' not in st.session_state:
        st.session_state.projects = [{
            'title': '',
            'link': '',
            'description': ['', '']
        }]
    
    if 'skills' not in st.session_state:
        st.session_state.skills = {
            'Programming Languages': '',
            'Tools & Technologies': '',
            'Soft Skills': ''
        }
    
    if 'achievements' not in st.session_state:
        st.session_state.achievements = ['', '']
    
    # Create tabs for different form sections
    tabs = st.tabs([
        "Basic Info",
        "Job Description",
        "Education",
        "Experience",
        "Skills",
        "Projects & Achievements",
        "Generate Resume"
    ])
    
    # Tab 1: Basic Information
    with tabs[0]:
        st.header("Personal Information")
        
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.user_profile['name'] = st.text_input("Full Name", st.session_state.user_profile['name'])
            st.session_state.user_profile['email'] = st.text_input("Email", st.session_state.user_profile['email'])
            st.session_state.user_profile['phone'] = st.text_input("Phone", st.session_state.user_profile['phone'])
        
        with col2:
            st.session_state.user_profile['linkedin'] = st.text_input("LinkedIn URL", st.session_state.user_profile['linkedin'])
            st.session_state.user_profile['github'] = st.text_input("GitHub URL", st.session_state.user_profile['github'])
            st.session_state.user_profile['location'] = st.text_input("Location", st.session_state.user_profile['location'])
    
    # Tab 2: Job Description
    with tabs[1]:
        st.header("Target Job")
        st.info("Paste the job description you're applying for. Our AI will analyze it to tailor your resume.")
        
        if 'job_description' not in st.session_state:
            st.session_state.job_description = ""
            
        st.session_state.job_description = st.text_area(
            "Job Description",
            st.session_state.job_description,
            height=300
        )
    
    # Tab 3: Education
    with tabs[2]:
        st.header("Education")
        
        for i, edu in enumerate(st.session_state.education):
            with st.container():
                st.subheader(f"Education #{i+1}")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.session_state.education[i]['institution'] = st.text_input(
                        "Institution",
                        edu['institution'],
                        key=f"edu_inst_{i}"
                    )
                    st.session_state.education[i]['degree'] = st.text_input(
                        "Degree",
                        edu['degree'],
                        key=f"edu_deg_{i}"
                    )
                    st.session_state.education[i]['gpa'] = st.text_input(
                        "GPA (Optional)",
                        edu['gpa'],
                        key=f"edu_gpa_{i}"
                    )
                
                with col2:
                    st.session_state.education[i]['location'] = st.text_input(
                        "Location",
                        edu['location'],
                        key=f"edu_loc_{i}"
                    )
                    st.session_state.education[i]['year'] = st.text_input(
                        "Graduation Year",
                        edu['year'],
                        key=f"edu_year_{i}"
                    )
                
                st.divider()
        
        # Add button to add more education entries
        if st.button("Add Another Education"):
            st.session_state.education.append({
                'institution': '',
                'degree': '',
                'year': '',
                'location': '',
                'gpa': ''
            })
            st.rerun()
        
        # Remove education entry if there's more than one
        if len(st.session_state.education) > 1:
            if st.button("Remove Last Education Entry"):
                st.session_state.education.pop()
                st.rerun()
    
    # Tab 4: Work Experience
    with tabs[3]:
        st.header("Work Experience")
        
        for i, exp in enumerate(st.session_state.experience):
            with st.container():
                st.subheader(f"Experience #{i+1}")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.session_state.experience[i]['title'] = st.text_input(
                        "Job Title",
                        exp['title'],
                        key=f"exp_title_{i}"
                    )
                    st.session_state.experience[i]['company'] = st.text_input(
                        "Company",
                        exp['company'],
                        key=f"exp_company_{i}"
                    )
                
                with col2:
                    st.session_state.experience[i]['duration'] = st.text_input(
                        "Duration (e.g., Jan 2020 - Present)",
                        exp['duration'],
                        key=f"exp_duration_{i}"
                    )
                    st.session_state.experience[i]['location'] = st.text_input(
                        "Location",
                        exp['location'],
                        key=f"exp_location_{i}"
                    )
                
                st.write("Responsibilities/Achievements (Use action verbs and quantify when possible)")
                
                # Ensure responsibilities list exists and has at least 3 items
                if 'responsibilities' not in st.session_state.experience[i]:
                    st.session_state.experience[i]['responsibilities'] = ['', '', ''] 
                
                # Add responsibilities as text inputs
                for j, resp in enumerate(st.session_state.experience[i]['responsibilities']):
                    st.session_state.experience[i]['responsibilities'][j] = st.text_input(
                        f"Bullet Point #{j+1}",
                        resp if j < len(st.session_state.experience[i]['responsibilities']) else "",
                        key=f"exp_resp_{i}_{j}"
                    )
                
                # Add more bullet points button
                if st.button(f"Add Bullet Point", key=f"add_bullet_{i}"):
                    st.session_state.experience[i]['responsibilities'].append("")
                    st.rerun()
                
                st.divider()
        
        # Add button to add more experience entries
        if st.button("Add Another Experience"):
            st.session_state.experience.append({
                'title': '',
                'company': '',
                'duration': '',
                'location': '',
                'responsibilities': ['', '', '']
            })
            st.rerun()
        
        # Remove experience entry if there's more than one
        if len(st.session_state.experience) > 1:
            if st.button("Remove Last Experience Entry"):
                st.session_state.experience.pop()
                st.rerun()
    
    # Tab 5: Skills
    with tabs[4]:
        st.header("Skills")
        st.info("Group your skills by category. Separate individual skills with commas.")
        
        # Loop through skill categories
        for category, skills in st.session_state.skills.items():
            st.session_state.skills[category] = st.text_area(
                f"{category}",
                skills,
                help=f"Enter your {category.lower()} separated by commas",
                key=f"skills_{category.replace(' ', '_').lower()}"
            )
        
        # Add custom skill category
        new_category = st.text_input("Add New Skill Category")
        if new_category and new_category not in st.session_state.skills:
            if st.button("Add Category"):
                st.session_state.skills[new_category] = ""
                st.rerun()
    
    # Tab 6: Projects and Achievements
    with tabs[5]:
        st.header("Projects")
        
        for i, proj in enumerate(st.session_state.projects):
            with st.container():
                st.subheader(f"Project #{i+1}")
                
                st.session_state.projects[i]['title'] = st.text_input(
                    "Project Title",
                    proj['title'],
                    key=f"proj_title_{i}"
                )
                
                st.session_state.projects[i]['link'] = st.text_input(
                    "Project Link (Optional)",
                    proj['link'],
                    key=f"proj_link_{i}"
                )
                
                st.write("Project Description (What did you build? What technologies did you use? What was the impact?)")
                
                # Ensure description list exists
                if 'description' not in st.session_state.projects[i]:
                    st.session_state.projects[i]['description'] = ['', '']
                
                # Add description points as text inputs
                for j, desc in enumerate(st.session_state.projects[i]['description']):
                    st.session_state.projects[i]['description'][j] = st.text_input(
                        f"Description Point #{j+1}",
                        desc if j < len(st.session_state.projects[i]['description']) else "",
                        key=f"proj_desc_{i}_{j}"
                    )
                
                # Add more description points button
                if st.button(f"Add Description Point", key=f"add_desc_{i}"):
                    st.session_state.projects[i]['description'].append("")
                    st.rerun()
                
                st.divider()
        
        # Add button to add more project entries
        if st.button("Add Another Project"):
            st.session_state.projects.append({
                'title': '',
                'link': '',
                'description': ['', '']
            })
            st.rerun()
        
        # Achievements section
        st.header("Achievements")
        st.info("List your certifications, awards, or other notable achievements.")
        
        for i, achievement in enumerate(st.session_state.achievements):
            st.session_state.achievements[i] = st.text_input(
                f"Achievement #{i+1}",
                achievement,
                key=f"achievement_{i}"
            )
        
        # Add more achievements button
        if st.button("Add Achievement"):
            st.session_state.achievements.append("")
            st.rerun()
    
    # Tab 7: Generate Resume
    # Tab 7: Generate Resume
    with tabs[6]:
        st.header("Generate Your Resume")
        
        # Check if essential fields are filled
        required_fields = [
            st.session_state.user_profile['name'],
            st.session_state.user_profile['email'],
            st.session_state.job_description
        ]
        
        # Check if at least one education entry is filled
        has_education = False
        for edu in st.session_state.education:
            if edu['institution'] and edu['degree']:
                has_education = True
                break
        
        # Check if at least one experience entry is filled
        has_experience = False
        for exp in st.session_state.experience:
            if exp['title'] and exp['company']:
                has_experience = True
                break
        
        if not all(required_fields) or not has_education:
            st.warning("Please fill in all required fields (name, email, job description, and at least one education entry)")
        else:
            st.success("All required fields are filled. Ready to generate your resume!")
            
            # Get API key from Streamlit secrets
            api_key = st.secrets.get("GEMINI_API_KEY", "")
            
            # Generate button
            if st.button("🚀 Generate ATS-Optimized Resume"):
                with st.spinner("Generating your resume... This may take a minute."):
                    try:
                        # Process and clean input data
                        processed_data = _process_form_data(
                            st.session_state.user_profile,
                            st.session_state.education,
                            st.session_state.experience,
                            st.session_state.projects,
                            st.session_state.skills,
                            st.session_state.achievements
                        )
                        
                        # Initialize resume builder crew
                        resume_builder = ResumeBuilderCrew(api_key=api_key)
                        
                        # Format achievements as string
                        achievements_str = "\n".join([a for a in st.session_state.achievements if a])
                        
                        # Format projects as string
                        projects_str = ""
                        for proj in st.session_state.projects:
                            if proj['title']:
                                projects_str += f"{proj['title']}"
                                if proj['link']:
                                    projects_str += f" (Link: {proj['link']})"
                                projects_str += "\n"
                                
                                for desc in proj['description']:
                                    if desc:
                                        projects_str += f"{desc}\n"
                                projects_str += "\n"
                        
                        # Build resume using the crew
                        result = resume_builder.build_resume(
                            user_profile=processed_data['user_profile'],
                            job_description=st.session_state.job_description,
                            projects=projects_str,
                            achievements=achievements_str
                        )
                        
                        # Extract results from CrewOutput object
                        if hasattr(result, 'output'):
                            result_dict = result.output
                        elif isinstance(result, dict):
                            result_dict = result
                        else:
                            result_dict = {'latex_code': '', 'pdf_binary': None}
                        
                        # Extract LaTeX code
                        latex_code = result_dict.get('latex_code', '')
                        
                        # Store results in session state
                        st.session_state.latex_code = latex_code
                        st.session_state.pdf_binary = result_dict.get('pdf_binary')
                        
                        # Display message
                        st.success("Resume generated successfully!")
                        
                        # Display tabs for viewing and downloading results
                        results_tabs = st.tabs(["LaTeX Code", "Download"])
                        
                        with results_tabs[0]:
                            st.code(latex_code, language="latex")
                        
                        with results_tabs[1]:
                            # Create converters for download links
                            pdf_converter = LaTeXPDFConverter()
                            
                            # Download options
                            st.markdown("### Download Options")
                            
                            # LaTeX download
                            latex_download = pdf_converter.create_download_link(
                                latex_code,
                                f"resume_{st.session_state.user_profile['name'].replace(' ', '_')}",
                                "latex"
                            )
                            st.markdown(latex_download, unsafe_allow_html=True)
                            
                            # PDF download if available
                            if st.session_state.pdf_binary:
                                pdf_download = pdf_converter.create_download_link(
                                    st.session_state.pdf_binary,
                                    f"resume_{st.session_state.user_profile['name'].replace(' ', '_')}",
                                    "pdf"
                                )
                                st.markdown(pdf_download, unsafe_allow_html=True)
                            else:
                                st.warning("PDF generation failed. You can download the LaTeX code and compile it manually.")
                                
                            # Instructions for manual compilation
                            with st.expander("How to compile LaTeX manually"):
                                st.markdown("""
                                1. Copy the LaTeX code from the tab above
                                2. Go to [Overleaf](https://www.overleaf.com/) and create a new project
                                3. Paste the LaTeX code into the editor
                                4. Click the "Compile" button to generate your PDF
                                5. Download the PDF from Overleaf
                                """)
                    
                    except Exception as e:
                        st.error(f"Error generating resume: {str(e)}")
                        st.error("Please check your inputs and try again.")

                        
def _process_form_data(user_profile, education, experience, projects, skills, achievements):
    """
    Process and clean form data for the resume builder
    
    Returns:
        dict: Dictionary with processed data
    """
    # Create a copy of user profile
    processed_profile = user_profile.copy()
    
    # Filter out empty education entries
    processed_education = []
    for edu in education:
        if edu['institution'] and edu['degree']:
            processed_education.append(edu)
    
    # Filter out empty experience entries and responsibilities
    processed_experience = []
    for exp in experience:
        if exp['title'] and exp['company']:
            exp_copy = exp.copy()
            # Filter out empty responsibilities
            processed_resp = [r for r in exp.get('responsibilities', []) if r]
            exp_copy['responsibilities'] = processed_resp
            processed_experience.append(exp_copy)
    
    # Filter out empty projects and descriptions
    processed_projects = []
    for proj in projects:
        if proj['title']:
            proj_copy = proj.copy()
            # Filter out empty descriptions
            processed_desc = [d for d in proj.get('description', []) if d]
            proj_copy['description'] = processed_desc
            processed_projects.append(proj_copy)
    
    # Process skills - remove empty categories
    processed_skills = {}
    for category, skills_list in skills.items():
        if skills_list.strip():
            processed_skills[category] = skills_list.strip()
    
    # Filter out empty achievements
    processed_achievements = [a for a in achievements if a]
    
    return {
        'user_profile': processed_profile,
        'education': processed_education,
        'experience': processed_experience,
        'projects': processed_projects,
        'skills': processed_skills,
        'achievements': processed_achievements
    }


if __name__ == "__main__":
    display_resume_builder_page()