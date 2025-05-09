
from crewai import Agent, Task, Crew, Process

import os
from crewai_tools import SerperDevTool
from crewai import LLM
import json
import re
import streamlit as st

# Set up API keys
os.environ['SERPER_API_KEY'] = st.secrets["SERPER_API_KEY"] 

# Initialize LLM
llm = LLM(
    model="gemini/gemini-2.0-flash-lite",  
    temperature=0.7,
    api_key=st.secrets["GEMINI_API_KEY"] 
)

# Initialize tools
serper_tool = SerperDevTool()

# AGENTS
profile_analyzer = Agent(
    role="User Profile Analyzer",
    goal=(
        "Thoroughly analyze user profiles to extract all relevant skills, experience, "
        "education, certifications, and knowledge areas. Create a comprehensive "
        "understanding of the user's current capabilities and expertise levels."
    ),
    verbose=True,
    memory=True,
    backstory=(
        "As a skilled profile analyzer with expertise in talent assessment, "
        "you excel at identifying a person's capabilities, knowledge areas, "
        "and skill levels from their profile information."
    ),
    tools=[serper_tool],
    llm=llm,
)

goal_analyzer = Agent(
    role="Learning Goal/Job Requirement Analyzer",
    goal=(
        "Analyze learning goals or job descriptions to identify all required "
        "skills, knowledge areas, prerequisites, and competency levels needed. "
        "Break down complex subjects into logical learning components and dependencies."
    ),
    verbose=True,
    memory=True,
    backstory=(
        "You are an expert in curriculum design and job market requirements. "
        "You can dissect any learning goal or job description to create a "
        "structured breakdown of all required skills and knowledge areas."
    ),
    tools=[serper_tool],
    llm=llm,
)

gap_analyzer = Agent(
    role="Learning Gap Analyzer",
    goal=(
        "Compare user's current skills against required skills to identify gaps. "
        "Prioritize learning needs based on importance, difficulty, and logical learning sequence. "
        "Focus on identifying the most efficient learning path."
    ),
    verbose=True,
    memory=True,
    backstory=(
        "You are a learning path optimization specialist who excels at identifying "
        "the most efficient route between current knowledge and learning goals. "
        "You understand skill dependencies and optimal learning sequences."
    ),
    llm=llm,
)

resource_finder = Agent(
    role="Learning Resource Finder",
    goal=(
        "Find high-quality learning resources for each skill gap identified. "
        "Provide a variety of resource types including websites, videos, practice questions, "
        "and learning platforms that match the user's learning needs."
    ),
    verbose=True,
    memory=True,
    backstory=(
        "You are an educational resource expert who knows where to find the best "
        "learning materials for any subject. You have extensive knowledge of online "
        "platforms, courses, tutorials, and practice resources across various domains."
    ),
    tools=[serper_tool],
    llm=llm,
)

roadmap_generator = Agent(
    role="Learning Roadmap Generator",
    goal=(
        "Create a clear, structured learning roadmap in markdown format that outlines "
        "the step-by-step progression from current skills to target skills. "
        "Organize content in a logical sequence with clear milestones."
    ),
    verbose=True,
    memory=True,
    backstory=(
        "You are a curriculum design expert who excels at creating clear learning paths. "
        "You know how to structure information in a way that makes the learning journey "
        "accessible and motivating."
    ),
    llm=llm,
)

report_compiler = Agent(
    role="Learning Roadmap Report Compiler",
    goal=(
        "Compile all insights into a comprehensive, well-structured "
        "report that guides the user through their personalized learning journey. "
        "Include timelines, resources, and actionable next steps."
    ),
    verbose=True,
    memory=True,
    backstory=(
        "You are a skilled educational content creator who excels at presenting "
        "complex information in clear, motivating formats. You know how to structure "
        "information to facilitate understanding and action."
    ),
    llm=llm,
)

# TASKS
profile_analysis_task = Task(
    description=(
        "Analyze the provided user profile to extract all relevant skills, experience, "
        "education, certifications, and knowledge areas. Create a structured JSON output "
        "of the user's current capabilities and expertise levels with detailed assessments "
        "of proficiency levels for each skill area.\n\n"
        "User Profile: {user_profile}"
    ),
    expected_output=(
        "A structured JSON containing:\n"
        "1. Basic user information summary\n"
        "2. Technical skills with proficiency levels (beginner, intermediate, advanced, expert)\n"
        "3. Soft skills with proficiency assessments\n"
        "4. Educational background\n"
        "5. Work experience highlights\n"
        "6. Certifications\n"
        "7. Knowledge areas and domains of expertise\n"
        "8. Overall strengths and potential growth areas"
    ),
    agent=profile_analyzer,
)

goal_analysis_task = Task(
    description=(
        "Analyze the provided learning goal or job description to identify all required "
        "skills, knowledge areas, prerequisites, and competency levels needed. Break down "
        "complex subjects into logical learning components with dependencies.\n\n"
        "Input: {learning_goal_or_job}"
    ),
    expected_output=(
        "A structured JSON containing:\n"
        "1. Summary of the learning goal or job requirements\n"
        "2. Core skills required with minimum proficiency levels\n"
        "3. Topic breakdown with subtopics and their dependencies\n"
        "4. Knowledge prerequisites for each major topic\n"
        "5. Logical learning sequence and dependencies\n"
        "6. Industry standards and best practices relevant to the goal\n"
        "7. Recommended depth of knowledge for each topic"
    ),
    agent=goal_analyzer,
    tools=[serper_tool],
)

gap_analysis_task = Task(
    description=(
        "Compare the user's current skills against required skills for their goal "
        "to identify gaps. Prioritize learning needs based on importance, difficulty, "
        "and logical learning sequence. Create a focused list of skills the user needs to develop.\n\n"
        "User profile analysis:"
        "Goal requirements analysis:"
    ),
    expected_output=(
        "A structured JSON containing:\n"
        "1. Summary of key skill gaps\n"
        "2. Prioritized list of skills to acquire\n"
        "3. Learning dependencies and prerequisites\n"
        "4. Topics the user can skip or review briefly based on existing knowledge\n"
        "5. Recommended focus areas with justification\n"
        "6. Logical learning sequence that builds upon existing knowledge"
    ),
    agent=gap_analyzer,
)

resource_finding_task = Task(
    description=(
        "For each skill gap identified, find high-quality learning resources including "
        "at least 2 website links, 2 YouTube tutorial links, and 2 practice question sources. "
        "Ensure resources are appropriate for the user's current level and target goal.\n\n"
        "Gap analysis:"
    ),
    expected_output=(
        "A structured JSON containing for each major skill gap:\n"
        "1. Skill name\n"
        "2. At least 2 website links with descriptions (documentation, tutorials, courses)\n"
        "3. At least 2 YouTube tutorial links with descriptions\n"
        "4. At least 2 practice question/exercise sources with descriptions\n"
        "5. Additional recommended resources like books, forums, GitHub repositories\n"
        "6. Brief explanation of why each resource is recommended"
    ),
    agent=resource_finder,
    tools=[serper_tool],
)

roadmap_generation_task = Task(
    description=(
        "Create a clear, structured markdown learning roadmap that outlines "
        "the step-by-step progression from current skills to target skills. "
        "Organize content in a logical sequence with clear milestones.\n\n"
        "Gap analysis:"
    ),
    expected_output=(
        "A comprehensive markdown roadmap containing:\n"
        "1. Overview of the learning journey\n"
        "2. Clear progression stages with estimated time commitments\n"
        "3. Skill dependencies shown through markdown formatting (headings, indentation)\n"
        "4. Milestones and checkpoints to track progress\n"
        "5. Prerequisites clearly marked for each stage\n"
        "6. Content organized to show progression from fundamentals to advanced topics"
    ),
    agent=roadmap_generator,
)

report_compilation_task = Task(
    description=(
        "Compile all insights into a comprehensive, well-structured markdown report "
        "that guides the user through their personalized learning journey. Include the roadmap, "
        "detailed skill analyses, and the curated learning resources.\n\n"
        "Profile analysis: \n"
        "Goal analysis: \n"
        "Gap analysis: \n"
        "Learning resources: \n"
        "Learning roadmap: "
    ),
    expected_output=(
        "A comprehensive learning roadmap report in markdown format containing:\n"
        "must include links"
        "Things to rembember Dont give Estimated time ot time taken to complete the learing just give the roadmap "
        "1. Executive summary of the personalized learning plan\n"
        "2. The learning roadmap section\n"
        "3. Detailed breakdown of learning stages\n"
        "4. Time estimates for each learning component\n"
        "5. Curated learning resources for each topic (websites, videos, practice questions)\n"
        "6. Milestones and progress tracking suggestions\n"
        "7. Tips for overcoming potential challenges\n"
        "8. Next steps to begin the learning journey"
    ),
    agent=report_compiler,
)

# CREW SETUP
def create_learning_roadmap_crew():
    """Create and return the learning roadmap crew"""
    return Crew(
        agents=[
            profile_analyzer,
            goal_analyzer,
            gap_analyzer, 
            resource_finder,
            roadmap_generator,
            report_compiler
        ],
        tasks=[
            profile_analysis_task,
            goal_analysis_task,
            gap_analysis_task,
            resource_finding_task,
            roadmap_generation_task,
            report_compilation_task
        ],
        process=Process.sequential,
        verbose=True,
    )

# MAIN FUNCTION
def generate_learning_roadmap(user_profile, learning_goal_or_job):
    """
    Generate a personalized learning roadmap based on user profile and learning goal/job description
    
    Args:
        user_profile (str): The user's profile information
        learning_goal_or_job (str): The learning goal or job description
        
    Returns:
        str: The complete learning roadmap report in markdown format
    """
    # Create the crew
    crew = create_learning_roadmap_crew()
    
    # Execute the workflow
    result = crew.kickoff(
        inputs={
            "user_profile": user_profile,
            "learning_goal_or_job": learning_goal_or_job,
        }
    )
    
    # The final result will be a markdown report with all sections included
    return str(result)


# Example usage
if __name__ == "__main__":
    # Example user profile
    user_profile = """
    Name: Jane Smith
    Education: Bachelor's in Computer Science, Stanford University (2020)
    
    Skills:
    - Python programming (4 years)
    - Data Analysis (3 years)
    - Machine Learning basics (1 year)
    - SQL (3 years)
    - Git (2 years)
    
    Work Experience:
    - Data Analyst at Tech Corp (2020-Present)
      * Analyzed customer data to identify trends
      * Built dashboards using Tableau
      * Performed A/B testing for product features
    
    Certifications:
    - Google Data Analytics Certificate
    - SQL for Data Science (Coursera)
    
    Projects:
    - Customer Churn Prediction Model using scikit-learn
    - Sales Forecasting Dashboard using Python and Tableau
    """
    
    # Example learning goal
    learning_goal = """
    I want to become a proficient AI engineer specializing in natural language processing.
    I'd like to be able to build and deploy production-ready NLP models that can analyze text, 
    generate content, and power conversational interfaces.
    """
    
    # Example job description
    job_description = """
    AI Engineer - Natural Language Processing
    
    Job Requirements:
    - 3+ years of experience in machine learning or deep learning
    - Strong understanding of NLP techniques and frameworks
    - Experience with transformer models like BERT, GPT, or T5
    - Proficiency in Python and PyTorch/TensorFlow
    - Experience with model deployment and MLOps
    - Knowledge of cloud services (AWS, GCP, or Azure)
    
    Responsibilities:
    - Develop and maintain NLP models for text analysis and generation
    - Improve model accuracy and performance through experimentation
    - Work with product teams to integrate NLP capabilities
    - Deploy models to production environments
    - Stay current with latest NLP research and techniques
    """
    
    # Generate the roadmap (using the learning goal in this example)
    roadmap_report = generate_learning_roadmap(user_profile, learning_goal)
    print(roadmap_report)
    
    print(f"Learning roadmap report generated successfully!")
