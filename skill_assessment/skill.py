# Add these imports at the top of the file
import sys
import os
__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import streamlit as st
import os
import json
import pandas as pd
import io
import base64
from io import BytesIO
import tempfile
from skill_assessment import skill_ass
import time
import altair as alt
import re   
# For PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet


def add_custom_css():
    """Add custom CSS styles to enhance the app's appearance"""
    st.markdown("""
    <style>
        /* General styling */
        .main {
            background-color: #f9fafb;
            padding: 1.5rem;
        }
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
            font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
        }
        h1, h2, h3 {
            color: #1e40af;
            font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
        }
        h1 {
            text-align: center;
            font-weight: 700;
            margin-bottom: 2rem;
            padding-bottom: 0.75rem;
            border-bottom: 3px solid #3b82f6;
        }
        /* Cards for sections */
        .card {
            background-color: white;
            border-radius: 12px;
            padding: 28px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            margin-bottom: 24px;
            border-left: 5px solid #3b82f6;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.08);
        }
        /* Skill ratings */
        .rating {
            font-family: system-ui, monospace;
            color: #3b82f6;
            letter-spacing: 2px;
        }
        /* Metric containers */
        .metric-container {
            background-color: #f1f8ff;
            border-left: 4px solid #3b82f6;
            padding: 16px;
            margin: 16px 0;
            border-radius: 0 10px 10px 0;
        }
        /* Override default button styles */
        .stButton>button {
            background-color: #3b82f6;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 0.9rem;
        }
        .stButton>button:hover {
            background-color: #1e40af;
            box-shadow: 0 4px 12px rgba(59,130,246,0.4);
            transform: translateY(-2px);
        }
        .stButton>button:active {
            transform: translateY(1px);
        }
        /* Upload area styling */
        [data-testid="stFileUploader"] {
            border: 2px dashed #3b82f6;
            border-radius: 12px;
            padding: 18px;
            background-color: #f8fafc;
            transition: all 0.3s ease;
        }
        [data-testid="stFileUploader"]:hover {
            border-color: #1e40af;
            background-color: #f0f7ff;
        }
        /* Success message */
        .success-message {
            background-color: #d1fae5;
            color: #065f46;
            padding: 16px;
            border-radius: 8px;
            margin: 18px 0;
            border-left: 5px solid #10b981;
            animation: fadeIn 0.5s ease-in-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        /* Tabs styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 16px;
            background-color: #f9fafb;
            padding: 8px;
            border-radius: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #f0f2f6;
            border-radius: 8px;
            padding: 10px 20px;
            height: auto;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        .stTabs [aria-selected="true"] {
            background-color: #3b82f6 !important;
            color: white !important;
            box-shadow: 0 2px 8px rgba(59,130,246,0.3);
        }
        .stTabs [data-baseweb="tab"]:hover:not([aria-selected="true"]) {
            background-color: #e0e7ff;
        }
        /* Progress bars */
        .stProgress > div > div {
            background-color: #3b82f6;
            background-image: linear-gradient(45deg, rgba(255,255,255,.15) 25%, transparent 25%, transparent 50%, rgba(255,255,255,.15) 50%, rgba(255,255,255,.15) 75%, transparent 75%, transparent);
            background-size: 1rem 1rem;
            animation: progress-bar-stripes 1s linear infinite;
        }
        @keyframes progress-bar-stripes {
            0% { background-position: 1rem 0; }
            100% { background-position: 0 0; }
        }
        /* Download links */
        a {
            color: #3b82f6;
            text-decoration: none;
            font-weight: 500;
            padding: 10px 18px;
            border: 1px solid #3b82f6;
            border-radius: 8px;
            display: inline-block;
            text-align: center;
            margin: 10px 0;
            transition: all 0.3s ease;
        }
        a:hover {
            background-color: #3b82f6;
            color: white;
            box-shadow: 0 2px 8px rgba(59,130,246,0.3);
        }
        /* Information callouts */
        .info-box {
            background-color: #e0f2fe;
            border-left: 5px solid #38bdf8;
            padding: 16px;
            margin: 16px 0;
            border-radius: 0 8px 8px 0;
        }
        /* Table styling improvements */
        table {
            border-collapse: separate;
            border-spacing: 0;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        th {
            background-color: #3b82f6 !important;
            color: white !important;
            font-weight: 600;
            padding: 12px !important;
        }
        td {
            padding: 12px !important;
        }
        tr:nth-child(even) {
            background-color: #f8fafc;
        }
        tr:hover {
            background-color: #f1f8ff;
        }
        /* Text inputs */
        .stTextInput input, .stTextArea textarea {
            border-radius: 8px;
            border: 1px solid #d1d5db;
            padding: 12px;
            transition: all 0.2s ease;
        }
        .stTextInput input:focus, .stTextArea textarea:focus {
            border-color: #3b82f6;
            box-shadow: 0 0 0 2px rgba(59,130,246,0.2);
        }
        /* Checkboxes and radio buttons */
        .stRadio label, .stCheckbox label {
            padding: 8px;
            cursor: pointer;
        }
        /* Spinner animation */
        .stSpinner svg {
            color: #3b82f6 !important;
        }
    </style>
    """, unsafe_allow_html=True)

def make_json_serializable(obj):
    """Convert any non-serializable objects to strings"""
    if hasattr(obj, '__class__') and obj.__class__.__name__ == 'CrewOutput':
        return str(obj)
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    else:
        return obj

def display_summary(results):
    """Display the summary results in a nicely formatted way"""
    summary = str(results.get("summary", "Summary not available"))
    
    # Display the markdown summary with custom styling
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(summary, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def create_skills_chart(skill_data):
    """Create a visual chart for skills data if possible"""
    # Check if skill_data is properly structured for visualization
    if not isinstance(skill_data, dict):
        return None
    
    # Extract skills data from the evaluation structure
    # Adjusted to handle the actual JSON structure
    if "evaluation" in skill_data:
        skills_dict = skill_data["evaluation"]
    else:
        return None
    
    # Extract and flatten skills data
    chart_data = []
    for category, skills in skills_dict.items():
        if isinstance(skills, dict):
            for skill_name, skill_info in skills.items():
                rating = None
                if isinstance(skill_info, dict) and "rating" in skill_info:
                    rating = skill_info["rating"]
                elif isinstance(skill_info, (int, float)):
                    rating = skill_info
                
                if rating is not None:
                    chart_data.append({
                        "Category": category.replace('_', ' ').title(),
                        "Skill": skill_name,
                        "Rating": rating
                    })
    
    if not chart_data:
        return None
    
    # Create dataframe from extracted data
    df = pd.DataFrame(chart_data)
    
    # Create and return chart with enhanced styling
    chart = alt.Chart(df).mark_bar().encode(
        y=alt.Y('Skill:N', sort='-x', title=None),
        x=alt.X('Rating:Q', scale=alt.Scale(domain=[0, 10]), title='Skill Rating (0-10)'),
        color=alt.Color('Category:N', 
                      legend=alt.Legend(orient="top", title=None),
                      scale=alt.Scale(scheme='blues')),
        tooltip=['Skill', 'Rating', 'Category']
    ).properties(
        title={
            "text": 'Skills Evaluation',
            "subtitle": "Based on resume analysis and job requirements",
            "fontSize": 20,
            "subtitleFontSize": 14,
            "anchor": "start",
            "subtitleColor": "gray"
        },
        height=30 * len(df) + 50 if len(df) > 0 else 300,
        width=600
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    ).configure_title(
        fontSize=20,
        font='Inter, Segoe UI, Arial',
        color='#1e40af'
    ).configure_view(
        strokeWidth=0
    )
    
    return chart

def display_full_analysis(results):
    """Display the full analysis results in tabbed sections"""
    tabs = st.tabs(["Resume Data", "Profile Data", "Skills Evaluation", "Job Match", "Evaluation Pipeline", "Interview Questions"])
    
    # Tab 1: Resume Data
    with tabs[0]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📄 Resume Information")
        
        resume_data = results.get("resume_data", {})
        if isinstance(resume_data, dict) and "raw_result" not in resume_data:
            # Display personal info if available
            if "personal_info" in resume_data:
                st.markdown("### Personal Information")
                personal_info = resume_data["personal_info"]
                for key, value in personal_info.items():
                    st.markdown(f"**{key.title()}:** {value}")
            
            # Check for personal_information key as well (matches JSON structure)
            if "personal_information" in resume_data:
                st.markdown("### Personal Information")
                personal_info = resume_data["personal_information"]
                for key, value in personal_info.items():
                    # Handle nested dictionaries like contact info
                    if isinstance(value, dict):
                        st.markdown(f"**{key.title()}:**")
                        for subkey, subvalue in value.items():
                            st.markdown(f"- **{subkey.title()}:** {subvalue}")
                    else:
                        st.markdown(f"**{key.title()}:** {value}")
                
            # Display skills if available
            if "skills" in resume_data:
                st.markdown("### Skills")
                skills = resume_data["skills"]
                if isinstance(skills, list):
                    st.markdown(", ".join(skills))
                elif isinstance(skills, dict):
                    for category, skill_list in skills.items():
                        st.markdown(f"**{category}:** {', '.join(skill_list)}")
                
            # Display experience if available
            if "experience" in resume_data:
                st.markdown("### Work Experience")
                for job in resume_data["experience"]:
                    if isinstance(job, dict):
                        company = job.get("company", "")
                        title = job.get("title", "")
                        period = job.get("period", "")
                        dates = job.get("dates", "")  # Added to match JSON structure
                        
                        # Use either period or dates
                        time_period = period if period else dates
                        
                        st.markdown(f"**{title}** at **{company}** ({time_period})")
                        
                        if "responsibilities" in job and job["responsibilities"]:
                            if isinstance(job["responsibilities"], list):
                                for resp in job["responsibilities"]:
                                    st.markdown(f"- {resp}")
                            else:
                                st.markdown(job["responsibilities"])
                    else:
                        st.markdown(f"- {job}")
            
            # Display education if available
            if "education" in resume_data:
                st.markdown("### Education")
                # Check if education is a dictionary or list
                if isinstance(resume_data["education"], dict):
                    edu = resume_data["education"]
                    degree = edu.get("degree", "")
                    institution = edu.get("institution", "")
                    year = edu.get("year", "")
                    dates = edu.get("dates", "")
                    location = edu.get("location", "")
                    cgpa = edu.get("cgpa", "")
                    
                    # Display education details
                    education_info = f"**{degree}** from **{institution}**"
                    if location:
                        education_info += f", {location}"
                    if year or dates:
                        education_info += f" ({year or dates})"
                    if cgpa:
                        education_info += f", CGPA: {cgpa}"
                    
                    st.markdown(education_info)
                else:
                    for edu in resume_data["education"]:
                        if isinstance(edu, dict):
                            degree = edu.get("degree", "")
                            institution = edu.get("institution", "")
                            year = edu.get("year", "")
                            
                            st.markdown(f"**{degree}** from **{institution}** ({year})")
                        else:
                            st.markdown(f"- {edu}")
            
            # Display projects if available
            if "projects" in resume_data:
                st.markdown("### Projects")
                for proj in resume_data["projects"]:
                    if isinstance(proj, dict):
                        name = proj.get("name", "")
                        description = proj.get("description", "")
                        technologies = proj.get("technologies", [])
                        link = proj.get("link", "")
                        
                        st.markdown(f"**{name}**")
                        st.markdown(description)
                        
                        if technologies:
                            st.markdown("**Technologies:**")
                            if isinstance(technologies, list):
                                for tech in technologies:
                                    st.markdown(f"- {tech}")
                            else:
                                st.markdown(technologies)
                        
                        if link:
                            st.markdown(f"**Link:** {link}")
                        
                        st.markdown("---")
                
            # Display certifications if available
            if "certifications" in resume_data:
                st.markdown("### Certifications")
                certs = resume_data["certifications"]
                if isinstance(certs, list):
                    for cert in certs:
                        if isinstance(cert, dict):
                            name = cert.get("name", "")
                            issuer = cert.get("issuer", "")
                            date = cert.get("date", "")
                            link = cert.get("link", "")
                            
                            cert_info = f"**{name}** from **{issuer}**"
                            if date:
                                cert_info += f" ({date})"
                            
                            st.markdown(cert_info)
                            
                            if link:
                                st.markdown(f"**Link:** {link}")
                        else:
                            st.markdown(f"- {cert}")
                else:
                    st.markdown(certs)
            
            # Display publications if available
            if "publications" in resume_data:
                st.markdown("### Publications")
                for pub in resume_data["publications"]:
                    if isinstance(pub, dict):
                        title = pub.get("title", "")
                        conference = pub.get("conference", "")
                        link = pub.get("link", "")
                        
                        st.markdown(f"**{title}**")
                        st.markdown(f"*Published in:* {conference}")
                        
                        if link:
                            st.markdown(f"**Link:** {link}")
                        
                        st.markdown("---")
                        
            # Display profiles if available
            if "profiles" in resume_data:
                st.markdown("### Online Profiles")
                profiles = resume_data["profiles"]
                if isinstance(profiles, dict):
                    for platform, username in profiles.items():
                        st.markdown(f"**{platform.title()}:** {username}")
        else:
            # Display raw text if structured data is not available
            st.json(resume_data)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Tab 2: Profile Data
    with tabs[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("👤 Profile Information")
        
        profile_data = results.get("profile_data", {})
        if profile_data:
            # GitHub data
            if "github" in profile_data:
                st.markdown("### GitHub Profile")
                github_data = profile_data["github"]
                
                # Create two columns
                col1, col2 = st.columns(2)
                
                if isinstance(github_data, dict):
                    with col1:
                        st.markdown(f"**Username:** {github_data.get('username', 'N/A')}")
                        st.markdown(f"**Name:** {github_data.get('name', 'N/A')}")
                        st.markdown(f"**Public Repos:** {github_data.get('public_repos', 'N/A')}")
                        st.markdown(f"**Profile Created:** {github_data.get('profile_created_at', 'N/A')}")
                    
                    with col2:
                        st.markdown(f"**Followers:** {github_data.get('followers', 'N/A')}")
                        st.markdown(f"**Following:** {github_data.get('following', 'N/A')}")
                        st.markdown(f"**Stars Received:** {github_data.get('starred_repos_count', 'N/A')}")
                        st.markdown(f"**Forks Received:** {github_data.get('forks_count', 'N/A')}")
                    
                    if "top_languages" in github_data:
                        st.markdown("**Top Languages:**")
                        st.markdown(", ".join(github_data["top_languages"]))
                    
                    if "bio" in github_data and github_data["bio"] != "Not available":
                        st.markdown(f"**Bio:** {github_data['bio']}")
                else:
                    st.markdown(github_data)
            
            # LeetCode data
            if "leetcode" in profile_data:
                st.markdown("### LeetCode Profile")
                leetcode_data = profile_data["leetcode"]
                
                if isinstance(leetcode_data, dict):
                    st.markdown(f"**Username:** {leetcode_data.get('username', 'N/A')}")
                    st.markdown(f"**Total Problems Solved:** {leetcode_data.get('total_problems_solved', 'N/A')}")
                    
                    # Problems by difficulty
                    if "problems_by_difficulty" in leetcode_data:
                        st.markdown("**Problems by Difficulty:**")
                        difficulties = leetcode_data["problems_by_difficulty"]
                        
                        cols = st.columns(len(difficulties) if isinstance(difficulties, dict) else 3)
                        if isinstance(difficulties, dict):
                            for i, (diff_name, count) in enumerate(difficulties.items()):
                                with cols[i % len(cols)]:
                                    st.metric(diff_name, count)
                    
                    st.markdown(f"**Ranking:** {leetcode_data.get('ranking', 'N/A')}")
                    
                    # Badges
                    if "badges" in leetcode_data and leetcode_data["badges"]:
                        st.markdown("**Badges:**")
                        st.markdown(", ".join(leetcode_data["badges"]))
                else:
                    st.markdown(leetcode_data)
            
            # Display other profiles if available
            for profile_type in ["geeksforgeeks", "hackerrank"]:
                if profile_type in profile_data:
                    st.markdown(f"### {profile_type.title()} Profile")
                    profile_info = profile_data[profile_type]
                    if isinstance(profile_info, dict):
                        for key, value in profile_info.items():
                            st.markdown(f"**{key.title()}:** {value}")
                    else:
                        st.markdown(f"{profile_info}")
        else:
            st.info("No profile information available")
            
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Tab 3: Skills Evaluation - Fixed to match the actual JSON structure
    with tabs[2]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🛠️ Skills Evaluation")
        
        skill_evaluation = results.get("skill_evaluation", {})
        
        # Try to create a visual chart from the skills data
        chart = create_skills_chart(skill_evaluation)
        if chart:
            st.altair_chart(chart, use_container_width=True)
        
        # Check if skill_evaluation has evaluation or raw_result
        if "evaluation" in skill_evaluation:
            evaluation_data = skill_evaluation["evaluation"]
            
            # Display skills by category
            for category, skills in evaluation_data.items():
                st.markdown(f"### {category.replace('_', ' ').title()}")
                
                if isinstance(skills, dict):
                    for skill_name, skill_info in skills.items():
                        if isinstance(skill_info, dict):
                            rating = skill_info.get("rating", "N/A")
                            evidence = skill_info.get("evidence", "")
                            notes = skill_info.get("notes", "")
                            
                            if isinstance(rating, (int, float)):
                                stars = "★" * int(rating) + "☆" * (10 - int(rating))
                                st.markdown(f"**{skill_name}:** {rating}/10 <span class='rating'>{stars}</span>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"**{skill_name}:** {rating}")
                            
                            if evidence:
                                st.markdown(f"*Evidence:* {evidence}")
                            if notes:
                                st.markdown(f"*Notes:* {notes}")
                        else:
                            st.markdown(f"**{skill_name}:** {skill_info}")
            
            # Display overall assessment if available
            if "overall_assessment" in skill_evaluation:
                st.markdown("### Overall Assessment")
                assessment = skill_evaluation["overall_assessment"]
                if isinstance(assessment, dict):
                    for key, value in assessment.items():
                        st.markdown(f"**{key.replace('_', ' ').title()}:**")
                        st.markdown(value)
        elif "raw_result" not in skill_evaluation:
            # Fall back to the original code structure for backward compatibility
            if "skills" in skill_evaluation:
                for category, skills in skill_evaluation["skills"].items():
                    st.markdown(f"### {category}")
                    
                    if isinstance(skills, dict):
                        for skill, rating in skills.items():
                            if isinstance(rating, (int, float)):
                                stars = "★" * int(rating) + "☆" * (10 - int(rating))
                                st.markdown(f"**{skill}:** {rating}/10 <span class='rating'>{stars}</span>", unsafe_allow_html=True)
                            elif isinstance(rating, dict):
                                skill_rating = rating.get("rating", "N/A")
                                evidence = rating.get("evidence", "")
                                stars = "★" * int(skill_rating) + "☆" * (10 - int(skill_rating))
                                st.markdown(f"**{skill}:** {skill_rating}/10 <span class='rating'>{stars}</span>", unsafe_allow_html=True)
                                if evidence:
                                    st.markdown(f"*Evidence:* {evidence}")
                    elif isinstance(skills, list):
                        for skill_item in skills:
                            if isinstance(skill_item, dict):
                                skill_name = skill_item.get("name", "")
                                skill_rating = skill_item.get("rating", "N/A")
                                evidence = skill_item.get("evidence", "")
                                
                                stars = "★" * int(skill_rating) + "☆" * (10 - int(skill_rating))
                                st.markdown(f"**{skill_name}:** {skill_rating}/10 <span class='rating'>{stars}</span>", unsafe_allow_html=True)
                                if evidence:
                                    st.markdown(f"*Evidence:* {evidence}")
            
            # Display analysis if available
            if "analysis" in skill_evaluation:
                st.markdown("### Analysis")
                analysis = skill_evaluation["analysis"]
                if isinstance(analysis, dict):
                    for key, value in analysis.items():
                        st.markdown(f"**{key.replace('_', ' ').title()}:**")
                        st.markdown(value)
                else:
                    st.markdown(analysis)
        else:
            # Display raw text if structured data is not available
            st.json(skill_evaluation)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Tab 4: Job Match - Fixed to match the actual JSON structure
    with tabs[3]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🎯 Job Match Analysis")
        
        job_match = results.get("job_match", {})
        
        # Extract the assessment data if available
        if "assessment" in job_match:
            job_match_data = job_match["assessment"]
            
            # Overall match percentage
            overall_match = job_match.get("overall_match_percentage") 
            if overall_match is not None:
                overall_pct = float(overall_match)
                st.markdown(f"<div style='text-align: center;'><h2>Overall Match: {overall_pct:.1f}%</h2></div>", unsafe_allow_html=True)
                st.progress(overall_pct/100)
            
            # Display detailed explanation if available
            detailed_explanation = job_match.get("detailed_explanation")
            if detailed_explanation:
                st.markdown(f"**Detailed Analysis:** {detailed_explanation}")
                st.markdown("---")
            
            # Essential requirements
            if "essential_requirements" in job_match_data:
                st.markdown("### Essential Requirements")
                essentials = job_match_data["essential_requirements"]
                
                if isinstance(essentials, dict):
                    for req, match_info in essentials.items():
                        if isinstance(match_info, dict):
                            match_pct = match_info.get("match_percentage", "")
                            details = match_info.get("details", match_info.get("explanation", ""))
                            
                            if isinstance(match_pct, (int, float)) or (isinstance(match_pct, str) and match_pct.replace('.', '', 1).isdigit()):
                                match_float = float(match_pct)
                                col1, col2 = st.columns([3, 7])
                                with col1:
                                    st.markdown(f"**{req.replace('_', ' ').title()}:**")
                                with col2:
                                    st.progress(match_float/100)
                                    st.markdown(f"{match_float:.1f}%")
                            else:
                                st.markdown(f"**{req.replace('_', ' ').title()}:** {match_pct}")
                            
                            if details:
                                st.markdown(f"*{details}*")
                                st.markdown("---")
                        else:
                            st.markdown(f"**{req.replace('_', ' ').title()}:** {match_info}")
                            st.markdown("---")
            
            # Preferred requirements
            if "preferred_requirements" in job_match_data:
                st.markdown("### Preferred Requirements")
                preferred = job_match_data["preferred_requirements"]
                
                if isinstance(preferred, dict):
                    for req, match_info in preferred.items():
                        if isinstance(match_info, dict):
                            match_pct = match_info.get("match_percentage", "")
                            details = match_info.get("details", match_info.get("explanation", ""))
                            
                            if isinstance(match_pct, (int, float)) or (isinstance(match_pct, str) and match_pct.replace('.', '', 1).isdigit()):
                                match_float = float(match_pct)
                                col1, col2 = st.columns([3, 7])
                                with col1:
                                    st.markdown(f"**{req.replace('_', ' ').title()}:**")
                                with col2:
                                    st.progress(match_float/100)
                                    st.markdown(f"{match_float:.1f}%")
                            else:
                                st.markdown(f"**{req.replace('_', ' ').title()}:** {match_pct}")
                            
                            if details:
                                st.markdown(f"*{details}*")
                                st.markdown("---")
                        else:
                            st.markdown(f"**{req.replace('_', ' ').title()}:** {match_info}")
                            st.markdown("---")
            
            # Experience level, cultural fit, growth potential
            for category in ["experience_level", "cultural_fit", "growth_potential"]:
                if category in job_match_data:
                    st.markdown(f"### {category.replace('_', ' ').title()}")
                    category_data = job_match_data[category]
                    
                    if isinstance(category_data, dict):
                        match_pct = category_data.get("match_percentage", "")
                        details = category_data.get("details", "")
                        
                        if isinstance(match_pct, (int, float)) or (isinstance(match_pct, str) and match_pct.replace('.', '', 1).isdigit()):
                            match_float = float(match_pct)
                            st.progress(match_float/100)
                            st.markdown(f"**Match: {match_float:.1f}%**")
                        else:
                            st.markdown(f"**Match:** {match_pct}")
                        
                        if details:
                            st.markdown(f"*{details}*")
        elif isinstance(job_match, dict) and "raw_result" not in job_match:
            # Fall back to original code structure for backward compatibility
            # Overall match percentage
            if "overall_match" in job_match:
                overall = job_match["overall_match"]
                if isinstance(overall, (int, float)) or (isinstance(overall, str) and overall.replace('.', '', 1).isdigit()):
                    overall_pct = float(overall)
                    st.markdown(f"<div style='text-align: center;'><h2>Overall Match: {overall_pct:.1f}%</h2></div>", unsafe_allow_html=True)
                    
                    # Progress bar for overall match
                    st.progress(overall_pct/100)
                else:
                    st.markdown(f"**Overall Match:** {overall}")
            
            # Essential requirements
            if "essential_requirements" in job_match:
                st.markdown("### Essential Requirements")
                essentials = job_match["essential_requirements"]
                
                if isinstance(essentials, dict):
                    for req, match_info in essentials.items():
                        if isinstance(match_info, dict):
                            match_pct = match_info.get("match_percentage", "")
                            explanation = match_info.get("explanation", "")
                            
                            if isinstance(match_pct, (int, float)) or (isinstance(match_pct, str) and match_pct.replace('.', '', 1).isdigit()):
                                match_float = float(match_pct)
                                col1, col2 = st.columns([3, 7])
                                with col1:
                                    st.markdown(f"**{req}:**")
                                with col2:
                                    st.progress(match_float/100)
                                    st.markdown(f"{match_float:.1f}%")
                            else:
                                st.markdown(f"**{req}:** {match_pct}")
                            
                            if explanation:
                                st.markdown(f"*{explanation}*")
                        else:
                            st.markdown(f"**{req}:** {match_info}")
        else:
            # Display raw result if structured data not available
            st.json(job_match)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Tab 5: Evaluation Pipeline
            # Tab 5: Evaluation Pipeline
        with tabs[4]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("📊 Evaluation Pipeline Results")
            
            evaluation_results = results.get("evaluation_results", {})
            
            if isinstance(evaluation_results, dict):
                # Get the pipeline data - note the key difference here
                pipeline = evaluation_results.get("evaluation_pipeline", {})
                
                # Display total score and recommendation if available
                if "overall" in pipeline:
                    overall = pipeline["overall"]
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if "total_score" in overall:
                            total_score = overall["total_score"]
                            st.markdown(f"<div style='text-align: center;'><h2>Total Score: {total_score}/100</h2></div>", unsafe_allow_html=True)
                            st.progress(float(total_score)/100)
                    
                    with col2:
                        if "recommendation" in overall:
                            recommendation = overall["recommendation"]
                            
                            # Color code based on recommendation text
                            if "proceed" in recommendation.lower():
                                st.markdown(f"<div style='text-align: center; background-color: #d4edda; padding: 10px; border-radius: 5px;'><h3>{recommendation}</h3></div>", unsafe_allow_html=True)
                            elif "hold" in recommendation.lower():
                                st.markdown(f"<div style='text-align: center; background-color: #fff3cd; padding: 10px; border-radius: 5px;'><h3>{recommendation}</h3></div>", unsafe_allow_html=True)
                            elif "reject" in recommendation.lower():
                                st.markdown(f"<div style='text-align: center; background-color: #f8d7da; padding: 10px; border-radius: 5px;'><h3>{recommendation}</h3></div>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"<div style='text-align: center;'><h3>{recommendation}</h3></div>", unsafe_allow_html=True)
                
                # Display stage results - adjusting for stage1, stage2 naming convention
                st.markdown("### Evaluation Stages")
                stages = ["stage1", "stage2", "stage3", "stage4"]
                stage_names = {
                    "stage1": "Basic Eligibility",
                    "stage2": "Skill Match", 
                    "stage3": "Domain Experience",
                    "stage4": "Role Fit"
                }
                
                # Create columns for the stages
                cols = st.columns(len(stages))
                
                for i, stage_key in enumerate(stages):
                    if stage_key in pipeline:
                        stage = pipeline[stage_key]
                        
                        with cols[i]:
                            st.markdown(f"<div style='text-align: center;'><h4>{stage.get('name', stage_names[stage_key])}</h4></div>", unsafe_allow_html=True)
                            
                            if isinstance(stage, dict):
                                score = stage.get("score", "N/A")
                                max_score = stage.get("max_score",100)
                                
                                st.markdown(f"<div style='text-align: center;'><h2>{score}/{max_score}</h2></div>", unsafe_allow_html=True)
                                
                                # Create progress bar
                                if isinstance(score, (int, float)) and max_score > 0:
                                    st.progress(float(score)/max_score)
                                
                                # Display justification if available
                                justification = stage.get("justification", "")
                                if justification:
                                    with st.expander("Justification"):
                                        st.markdown(justification)
                                
                                # Display key factors if available
                                key_factors = stage.get("key_factors", {})
                                if key_factors and isinstance(key_factors, dict):
                                    with st.expander("Key Factors"):
                                        for factor_key, factor_value in key_factors.items():
                                            if isinstance(factor_value, dict):
                                                st.markdown(f"**{factor_key.replace('_', ' ').title()}:**")
                                                for sub_key, sub_value in factor_value.items():
                                                    st.markdown(f"- {sub_key}: {sub_value}")
                                            else:
                                                st.markdown(f"**{factor_key.replace('_', ' ').title()}:** {factor_value}")
            else:
                # Display raw result if structured data not available
                st.json(evaluation_results)
            
            st.markdown('</div>', unsafe_allow_html=True)

    # Tab 6: Interview Questions
    with tabs[5]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🎯 Technical Interview Questions")
        
        questions = results.get("interview_questions", {})
        
        # Handle different formats of interview questions data
        if isinstance(questions, dict):
            if "questions" in questions:
                questions_list = questions["questions"]
            elif "raw_result" in questions:
                # Try to extract JSON from the raw result
                import re
                import json
                json_match = re.search(r'```json\n(.*?)\n```', questions["raw_result"], re.DOTALL)
                if json_match:
                    try:
                        extracted_json = json.loads(json_match.group(1))
                        if "questions" in extracted_json:
                            questions_list = extracted_json["questions"]
                        else:
                            questions_list = extracted_json
                    except:
                        questions_list = []
                else:
                    # If no JSON found, try to parse questions by pattern
                    question_pattern = r'(\d+[\)\.]\s*.*?(?:\?|:))([^0-9]*(?=\d+[\)\.]\s*|$))'
                    matches = re.findall(question_pattern, questions["raw_result"], re.DOTALL)
                    questions_list = [{"question": q.strip(), "explanation": e.strip()} for q, e in matches]
            else:
                # Assume the dict itself contains the questions
                questions_list = [questions]
        elif isinstance(questions, list):
            questions_list = questions
        elif isinstance(questions, str):
            # Try to convert string to JSON if possible
            try:
                questions_list = json.loads(questions)
                if isinstance(questions_list, dict) and "questions" in questions_list:
                    questions_list = questions_list["questions"]
            except:
                st.write(questions)
                st.markdown('</div>', unsafe_allow_html=True)
                return
        else:
            st.write("Questions format not recognized.")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        
        if isinstance(questions_list, list):
            for i, q in enumerate(questions_list):
                if isinstance(q, dict):
                    question = q.get("question", "")
                    difficulty = q.get("difficulty", "")
                    assessment = q.get("assessment", "")
                    guidance = q.get("guidance", "")
                    
                    # Display question with nice formatting
                    st.markdown(f"### Q{i+1}: {question}")
                    
                    col1, col2 = st.columns(2)
                    if difficulty:
                        with col1:
                            st.markdown(f"**Difficulty:** {difficulty}")
                    
                    if assessment:
                        with col2:
                            st.markdown(f"**Assessing:** {assessment}")
                    
                    if guidance:
                        st.markdown(f"**Guidance:** {guidance}")
                    
                    st.markdown("---")
                else:
                    # If it's just a string
                    st.markdown(f"### Q{i+1}: {q}")
                    st.markdown("---")
        
        st.markdown('</div>', unsafe_allow_html=True)

def download_results(results):
    """Create a downloadable JSON file of the analysis results"""
    # Make results JSON serializable
    serializable_results = make_json_serializable(results)
    
    # Convert to JSON
    json_results = json.dumps(serializable_results, indent=4)
    
    # Create a download button
    b64 = base64.b64encode(json_results.encode()).decode()
    href = f'<a href="data:application/json;base64,{b64}" download="resume_analysis_results.json">Download Results (JSON)</a>'
    return href

def download_report_pdf(results):
    """Generate a PDF report of the analysis results"""
    try:
        # Create a BytesIO object to store the PDF
        pdf_buffer = BytesIO()
        
        # Create the PDF document using ReportLab
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        # Custom styles
        title_style = styles["Heading1"]
        heading2_style = styles["Heading2"]
        heading3_style = styles["Heading3"]
        normal_style = styles["Normal"]
        
        # Add title
        elements.append(Paragraph("Resume Analysis Report", title_style))
        elements.append(Spacer(1, 12))
        
        # Add summary - convert Markdown to plain text or handle it properly
        elements.append(Paragraph("Executive Summary", heading2_style))
        elements.append(Spacer(1, 6))
        
        # Get summary and handle it properly (remove Markdown/HTML)
        summary = str(results.get("summary", "Summary not available"))
        # Remove Markdown headings and other formatting
        summary = re.sub(r'#{1,6}\s+', '', summary)  # Remove Markdown headings
        summary = re.sub(r'\*\*(.*?)\*\*', r'\1', summary)  # Remove bold
        summary = re.sub(r'\*(.*?)\*', r'\1', summary)  # Remove italic
        summary = re.sub(r'<.*?>', '', summary)  # Remove HTML tags
        
        # Split by paragraphs and add each as a separate paragraph
        for para in summary.split('\n\n'):
            if para.strip():  # Only add non-empty paragraphs
                elements.append(Paragraph(para.strip(), normal_style))
                elements.append(Spacer(1, 6))
        
        elements.append(Spacer(1, 15))
        
        # Add skills evaluation
        elements.append(Paragraph("Skills Evaluation", heading2_style))
        elements.append(Spacer(1, 6))
        
        skill_eval = results.get("skill_evaluation", {})
        
        # Check if skill_evaluation contains 'evaluation' key
        if "evaluation" in skill_eval:
            for category, skills in skill_eval["evaluation"].items():
                elements.append(Paragraph(f"{category.replace('_', ' ').title()}", heading3_style))
                elements.append(Spacer(1, 6))
                
                if isinstance(skills, dict):
                    # Create a table for skills
                    data = [["Skill", "Rating", "Evidence"]]
                    for skill, skill_info in skills.items():
                        if isinstance(skill_info, dict):
                            rating = skill_info.get("rating", "N/A")
                            evidence = skill_info.get("evidence", "")
                            # Clean evidence from HTML/Markdown if needed
                            evidence = re.sub(r'<.*?>', '', str(evidence))
                            data.append([skill, f"{rating}/10", evidence])
                        elif isinstance(skill_info, (int, float)):
                            data.append([skill, f"{skill_info}/10", ""])
                        else:
                            data.append([skill, str(skill_info), ""])
                    
                    # Create the table if we have data
                    if len(data) > 1:
                        table = Table(data, colWidths=[120, 60, 320])
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        elements.append(table)
                        elements.append(Spacer(1, 12))
        
        # Add overall assessment if available
        if "overall_assessment" in skill_eval:
            elements.append(Paragraph("Skills Analysis", heading3_style))
            elements.append(Spacer(1, 6))
            
            for key, value in skill_eval["overall_assessment"].items():
                elements.append(Paragraph(f"{key.replace('_', ' ').title()}", heading3_style))
                
                # Handle different value types
                if isinstance(value, list):
                    # For lists, add each item as a separate paragraph
                    for item in value:
                        clean_item = re.sub(r'<.*?>', '', str(item))  # Remove HTML tags
                        elements.append(Paragraph(clean_item, normal_style))
                else:
                    # For strings, remove HTML tags and add as paragraph
                    clean_value = re.sub(r'<.*?>', '', str(value))  # Remove HTML tags
                    elements.append(Paragraph(clean_value, normal_style))
                
                elements.append(Spacer(1, 6))
        

        
        # Add job match
        elements.append(Paragraph("Job Match Analysis", heading2_style))
        elements.append(Spacer(1, 6))
        
        job_match = results.get("job_match", {})
        if job_match:
            # Overall match
            if "overall_match_percentage" in job_match:
                overall = job_match["overall_match_percentage"]
                elements.append(Paragraph(f"Overall Match: {overall}%", heading3_style))
                elements.append(Spacer(1, 6))
            
            # Detailed explanation
            if "detailed_explanation" in job_match:
                elements.append(Paragraph("Detailed Explanation", heading3_style))
                elements.append(Paragraph(job_match["detailed_explanation"], normal_style))
                elements.append(Spacer(1, 12))
            
            # Assessment breakdown
            if "assessment" in job_match:
                assessment = job_match["assessment"]
                
                # Essential requirements
                if "essential_requirements" in assessment:
                    elements.append(Paragraph("Essential Requirements", heading3_style))
                    elements.append(Spacer(1, 6))
                    
                    essentials = assessment["essential_requirements"]
                    data = [["Requirement", "Match %", "Details"]]
                    
                    for req, info in essentials.items():
                        match_pct = info.get("match_percentage", "N/A")
                        details = info.get("details", "")
                        data.append([req.replace("_", " ").title(), f"{match_pct}%", details])
                    
                    if len(data) > 1:
                        table = Table(data, colWidths=[120, 60, 320])
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        elements.append(table)
                        elements.append(Spacer(1, 12))
                
                # Preferred requirements
                if "preferred_requirements" in assessment:
                    elements.append(Paragraph("Preferred Requirements", heading3_style))
                    elements.append(Spacer(1, 6))
                    
                    preferred = assessment["preferred_requirements"]
                    data = [["Requirement", "Match %", "Details"]]
                    
                    for req, info in preferred.items():
                        match_pct = info.get("match_percentage", "N/A")
                        details = info.get("details", "")
                        data.append([req.replace("_", " ").title(), f"{match_pct}%", details])
                    
                    if len(data) > 1:
                        table = Table(data, colWidths=[120, 60, 320])
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        elements.append(table)
                        elements.append(Spacer(1, 12))
        
        # Add evaluation results
        elements.append(Paragraph("Evaluation Results", heading2_style))
        elements.append(Spacer(1, 6))
        
        eval_results = results.get("evaluation_results", {})
        if "evaluation_pipeline" in eval_results:
            pipeline = eval_results["evaluation_pipeline"]
            
            # Overall evaluation
            if "overall" in pipeline:
                overall = pipeline["overall"]
                total_score = overall.get("total_score", "N/A")
                recommendation = overall.get("recommendation", "Not available")
                
                elements.append(Paragraph(f"Total Score: {total_score}/100", heading3_style))
                elements.append(Spacer(1, 6))
                elements.append(Paragraph(f"Recommendation: {recommendation}", heading3_style))
                elements.append(Spacer(1, 12))
            
            # Evaluation stages
            data = [["Evaluation Stage", "Score", "Justification"]]
            for key, stage in pipeline.items():
                if key != "overall" and isinstance(stage, dict):
                    name = stage.get("name", key)
                    score = f"{stage.get('score', 'N/A')}/{stage.get('max_score', 'N/A')}"
                    justification = stage.get("justification", "")
                    data.append([name, score, justification])
            
            if len(data) > 1:
                table = Table(data, colWidths=[150, 60, 290])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(table)
                elements.append(Spacer(1, 12))
        
        # Add interview questions
        interview_questions = results.get("interview_questions", {}).get("questions", [])
        if interview_questions:
            elements.append(Paragraph("Recommended Interview Questions", heading2_style))
            elements.append(Spacer(1, 6))
            
            for i, question_data in enumerate(interview_questions, 1):
                question = question_data.get("question", "")
                if question:
                    elements.append(Paragraph(f"{i}. {question}", normal_style))
                    elements.append(Spacer(1, 6))
        
        # Build the PDF
        doc.build(elements)
        
        # Reset buffer position
        pdf_buffer.seek(0)
        
        # Create download button
        b64 = base64.b64encode(pdf_buffer.getvalue()).decode()
        href = f'<a href="data:application/pdf;base64,{b64}" download="resume_analysis_report.pdf">Download Report (PDF)</a>'
        return href
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        st.error(f"Error generating PDF: {str(e)}")
        st.error(f"Error details: {error_details}")
        return ""
    
def main():
    """Main function to run the Streamlit app"""
    # Add custom CSS
    add_custom_css()
    
    # App header with enhanced styling
    st.markdown("""
    <div style="text-align: center; padding: 32px 0 20px;">
        <h1 style="color: #1e40af; font-size: 2.7rem; font-weight: 700; margin-bottom: 16px;">
            <span style="background: linear-gradient(90deg, #3b82f6, #1e40af); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                AI Skill Assessment System
            </span>
            <span style="font-size: 2.7rem; margin-left: 5px;">🚀</span>
        </h1>
        <p style="font-size: 1.2rem; color: #4b5563; max-width: 700px; margin: 0 auto; line-height: 1.6;">
            Upload a resume and job description to get an AI-powered analysis of skills, experience, and job fit.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs with enhanced styling
    tabs = st.tabs(["📤 Upload", "📊 Analysis", "ℹ️ About"])
    
    with tabs[0]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("""
        <h2 style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.8rem;">📤</span> Upload Files
        </h2>
        """, unsafe_allow_html=True)
        
        # Resume upload
        st.markdown("""
        <div style="background-color: #f0f7ff; padding: 16px; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="margin-top: 0; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.3rem;">📄</span> Resume
            </h3>
            <p style="margin-bottom: 10px; color: #4b5563;">
                Upload your resume in PDF, DOCX or TXT format
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        resume_file = st.file_uploader("", type=["pdf", "docx", "txt"])
        
        # Job description input
        st.markdown("""
        <div style="background-color: #f0f7ff; padding: 16px; border-radius: 10px; margin: 24px 0 12px;">
            <h3 style="margin-top: 0; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.3rem;">📋</span> Job Description
            </h3>
            <p style="margin-bottom: 10px; color: #4b5563;">
                Enter the job requirements or use our sample
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        job_description_option = st.radio(
            "Choose an option:",
            ["Enter job description", "Use sample job description"],
            horizontal=True
        )
        
        if job_description_option == "Enter job description":
            job_requirements = st.text_area(
                "Enter job requirements:",
                height=200,
                placeholder="Enter the job description including requirements, responsibilities, etc."
            )
        else:
            job_requirements = skill_ass.sample_job_requirements
            st.text_area("Sample job description:", value=job_requirements, height=200, disabled=True)
        
        # Analysis button
        analyze_button = st.button("Analyze Resume", type="primary", use_container_width=True)
        
        # In the main function, in the analyze_button handler:
        if analyze_button:
            if resume_file is not None and job_requirements:
                try:
                    # Save uploaded file temporarily
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{resume_file.name.split('.')[-1]}") as tmp_file:
                        tmp_file.write(resume_file.getvalue())
                        temp_path = tmp_file.name
                    
                    # Display progress with enhanced styling
                    progress_container = st.container()
                    with progress_container:
                        st.markdown("""
                        <div style="text-align: center; margin: 16px 0; background-color: #f0f7ff; padding: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);">
                            <h3 style="color: #1e40af; margin-top: 0;">Processing Resume</h3>
                            <p style="color: #4b5563; margin-bottom: 20px;">We're analyzing your resume data. This might take a moment.</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Create a spinner for visual feedback
                        with st.spinner('Processing...'):
                            # Analysis started
                            status_text.markdown('<div style="text-align: center; color: #4b5563; padding: 10px; font-weight: 500;">Starting analysis...</div>', unsafe_allow_html=True)
                            progress_bar.progress(10)
                            time.sleep(0.5)  # Small delay for visual feedback
                            
                            # Run the assessment
                            status_text.markdown('<div style="text-align: center; color: #4b5563; padding: 10px; font-weight: 500;">Extracting resume data...</div>', unsafe_allow_html=True)
                            progress_bar.progress(20)
                            time.sleep(0.5)
                            
                            # Open the file in binary mode
                            with open(temp_path, "rb") as file:
                                status_text.markdown('<div style="text-align: center; color: #4b5563; padding: 10px; font-weight: 500;">Analyzing skills and experience...</div>', unsafe_allow_html=True)
                                progress_bar.progress(40)
                                
                                # Call the function from skill_ass.py
                                results = skill_ass.run_skill_assessment(file, job_requirements)

                                
                                status_text.markdown('<div style="text-align: center; color: #4b5563; padding: 10px; font-weight: 500;">Evaluating job fit...</div>', unsafe_allow_html=True)
                                progress_bar.progress(70)
                                time.sleep(0.5)
                                
                                status_text.markdown('<div style="text-align: center; color: #4b5563; padding: 10px; font-weight: 500;">Generating recommendations...</div>', unsafe_allow_html=True)
                                progress_bar.progress(85)
                                time.sleep(0.5)
                                
                                status_text.markdown('<div style="text-align: center; color: #4b5563; padding: 10px; font-weight: 500;">Creating final report...</div>', unsafe_allow_html=True)
                                progress_bar.progress(95)
                                time.sleep(0.5)
                                
                                # Save results to session state
                                st.session_state.results = results
                                st.session_state.analysis_complete = True
                                
                                # Complete
                                status_text.markdown('<div style="text-align: center; color: #065f46; font-weight: bold; padding: 10px;">Analysis complete!</div>', unsafe_allow_html=True)
                                progress_bar.progress(100)
                            
                            # Show success message with enhanced styling
                            st.markdown("""
                            <div style="background-color: #d1fae5; padding: 20px; border-radius: 10px; border-left: 5px solid #10b981; margin-top: 24px; animation: fadeIn 0.5s ease-in-out;">
                                <div style="display: flex; align-items: center; gap: 12px;">
                                    <span style="font-size: 1.5rem; color: #059669;">✅</span>
                                    <div>
                                        <p style="color: #065f46; font-weight: 600; margin: 0; font-size: 1.1rem;">Analysis completed successfully!</p>
                                        <p style="color: #065f46; margin: 5px 0 0;">Go to the Analysis tab to view your detailed results.</p>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                    
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
            else:
                if resume_file is None:
                    st.warning("Please upload a resume file.")
                if not job_requirements:
                    st.warning("Please enter or select a job description.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tabs[1]:
        if 'analysis_complete' in st.session_state and st.session_state.analysis_complete:
            results = st.session_state.results
            
            # Create two columns for the summary and download buttons
            col1, col2 = st.columns([7, 3])
            
            with col1:
                st.markdown("""
                <h2 style="color: #1e40af; display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.8rem;">📊</span> Analysis Results
                </h2>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                <div style="background-color: #f0f7ff; padding: 16px; border-radius: 10px; text-align: center; margin-top: 10px;">
                    <p style="margin-bottom: 12px; color: #1e40af; font-weight: 500;">Download Your Results</p>
                """, unsafe_allow_html=True)
                st.markdown(download_results(results), unsafe_allow_html=True)
                st.markdown(download_report_pdf(results), unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Display the summary
            st.markdown("""
            <h3 style="color: #1e40af; margin-top: 30px; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.5rem;">📝</span> Executive Summary
            </h3>
            """, unsafe_allow_html=True)
            display_summary(results)            
            
            # Display the full analysis
            st.markdown("""
            <h3 style="color: #1e40af; margin-top: 30px; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.5rem;">🔍</span> Detailed Analysis
            </h3>
            """, unsafe_allow_html=True)
            display_full_analysis(results)
            
        else:
            st.markdown("""
            <div style="text-align: center; padding: 60px 20px; background-color: #f0f7ff; border-radius: 12px; margin: 30px 0;">
                <img src="https://img.icons8.com/fluency/96/000000/upload-to-cloud.png" style="width: 80px; height: 80px; margin-bottom: 20px;" />
                <h2 style="color: #1e40af; margin-bottom: 12px;">No Analysis Results Yet</h2>
                <p style="color: #4b5563; font-size: 1.1rem; max-width: 600px; margin: 0 auto;">
                    Please upload a resume and job description in the Upload tab to see analysis results.
                </p>
                <div style="margin-top: 30px;">
                    <a href="#" onclick="document.querySelector('[data-baseweb=\'tab\']:not([aria-selected=\'true\'])').click(); return false;" 
                       style="background-color: #3b82f6; color: white; border: none; box-shadow: 0 2px 8px rgba(59,130,246,0.3);">
                       Go to Upload
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with tabs[2]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("""
        <h2 style="color: #1e40af; display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.8rem;">ℹ️</span> About AI Resume Analyzer
        </h2>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background-color: #f0f7ff; padding: 20px; border-radius: 10px; margin-bottom: 24px;">
            <h3 style="color: #1e40af; margin-top: 0;">What We Do</h3>
            <p style="margin-bottom: 0; line-height: 1.6;">
                This application uses advanced AI to analyze resumes and job descriptions, bridging the gap between candidates and employers with objective, data-driven insights.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Create three columns for benefits
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div style="background-color: white; border-left: 4px solid #3b82f6; padding: 16px; border-radius: 0 10px 10px 0; height: 100%; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <h4 style="color: #1e40af; display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.5rem;">👔</span> For Recruiters
                </h4>
                <p style="color: #4b5563;">
                    Evaluate candidate skills and job fit quickly and objectively, saving time in the screening process.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div style="background-color: white; border-left: 4px solid #3b82f6; padding: 16px; border-radius: 0 10px 10px 0; height: 100%; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <h4 style="color: #1e40af; display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.5rem;">👤</span> For Candidates
                </h4>
                <p style="color: #4b5563;">
                    Understand how your resume matches job requirements and identify areas for improvement.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown("""
            <div style="background-color: white; border-left: 4px solid #3b82f6; padding: 16px; border-radius: 0 10px 10px 0; height: 100%; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <h4 style="color: #1e40af; display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.5rem;">🧠</span> For Hiring Managers
                </h4>
                <p style="color: #4b5563;">
                    Create better interview questions based on candidate profiles and identified skill gaps.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("""
        <div style="margin-top: 30px;">
            <h3 style="color: #1e40af;">How It Works</h3>
            
            <div style="display: flex; align-items: center; margin: 20px 0; background-color: white; padding: 16px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="background-color: #3b82f6; color: white; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-right: 16px;">1</div>
                <div>
                    <h4 style="margin: 0; color: #1e40af;">Upload a resume</h4>
                    <p style="margin: 5px 0 0; color: #4b5563;">in PDF, DOCX, or TXT format</p>
                </div>
            </div>
            
            <div style="display: flex; align-items: center; margin: 20px 0; background-color: white; padding: 16px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="background-color: #3b82f6; color: white; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-right: 16px;">2</div>
                <div>
                    <h4 style="margin: 0; color: #1e40af;">Enter a job description</h4>
                    <p style="margin: 5px 0 0; color: #4b5563;">with requirements and responsibilities</p>
                </div>
            </div>
            
            <div style="display: flex; align-items: center; margin: 20px 0; background-color: white; padding: 16px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="background-color: #3b82f6; color: white; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-right: 16px;">3</div>
                <div>
                    <h4 style="margin: 0; color: #1e40af;">Get an AI-powered analysis</h4>
                    <p style="margin: 5px 0 0; color: #4b5563;">including skill evaluations, job match analysis, and recommendations</p>
                </div>
            </div>
        </div>
        
        <div style="margin-top: 30px; background-color: #e0f2fe; padding: 20px; border-radius: 10px; border-left: 5px solid #38bdf8;">
            <h3 style="color: #0c4a6e; margin-top: 0;">Privacy & Data</h3>
            <p style="color: #0e7490; margin-bottom: 0;">
                All data is processed temporarily and not stored permanently. Analysis results can be downloaded for your records.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def load():
    main() 
