# resume_builder_agent.py
from crewai import Agent, Task, Crew, Process
import os
from crewai import LLM
import json
import re
from utils.input import DateTimeEncoder # cls=DateTimeEncoder

class ResumeBuilderCrew:
    def __init__(self, api_key):
        """Initialize the Resume Builder Crew with API key"""
        self.llm = LLM(
            model="gemini/gemini-2.0-flash-lite",
            temperature=0.7,
            api_key=api_key
        )
    
    def create_agents(self):
        """Create the agents for the resume building process"""
        
        # Resume Expert Agent
        resume_expert = Agent(
            role="ATS Resume Expert",
            goal="Create ATS-friendly resumes that maximize interview callback rates",
            backstory="""You are a highly experienced resume writer with 15+ years of experience
            helping candidates get past Applicant Tracking Systems (ATS) and land interviews.
            You know exactly how to optimize resumes for relevant keywords, structure them properly,
            and highlight achievements in a way that appeals to both ATS systems and human recruiters.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=False
        )
        
        # Job Description Analyzer Agent
        job_analyzer = Agent(
            role="Job Description Analyzer",
            goal="Extract key skills, requirements, and priorities from job descriptions",
            backstory="""You are an expert at analyzing job descriptions and identifying exactly what 
            employers are looking for. You can extract key requirements, must-have skills, preferred
            qualifications, and even the hidden priorities that aren't explicitly stated. Your analysis
            ensures resumes can be perfectly tailored to specific positions.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=True
        )
        
        # Resume Formatter Agent
        resume_formatter = Agent(
            role="Resume Formatter",
            goal="Structure and format resumes for optimal ATS parsing and visual appeal",
            backstory="""You are a formatting and design expert who knows exactly how to structure
            resumes for maximum readability by both ATS systems and human recruiters. You understand
            which formats work best, how to organize sections, and how to ensure all critical information
            is presented in a way that's easy to scan and absorb.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=True
        )
        
        return [resume_expert, job_analyzer, resume_formatter]
    
    def create_tasks(self, agents, user_profile, job_description, projects, achievements):
        """Create tasks for the resume building process"""
        
        # Unpack agents
        resume_expert, job_analyzer, resume_formatter = agents
        
        # Task 1: Analyze Job Description
        analyze_job = Task(
            description=f"""Analyze the job description carefully to extract:
            1. Required skills and qualifications
            2. Preferred skills and experience
            3. Key responsibilities
            4. Industry-specific keywords and phrases
            5. Soft skills that appear important for the role
            
            Job Description:
            {job_description}
            
            Provide a structured analysis that can be used to optimize a resume.
            """,
            agent=job_analyzer,
            expected_output="""A detailed analysis of the job description with lists of:
            - Required technical skills
            - Required soft skills
            - Key responsibilities
            - Important keywords
            - Industry-specific terminology
            """
        )
        
        # Task 2: Tailor Resume Content
        tailor_resume = Task(
            description=f"""Using the job description analysis and the candidate's profile, create tailored content for each section of the resume.
            
            IMPORTANT: This resume MUST fit on a single page. Be concise and focus on the most relevant information.
            
            Candidate Profile:
            {json.dumps(user_profile, indent=2, cls=DateTimeEncoder)}
            
            Projects:
            {projects}
            
            Achievements:
            {achievements}
            
            Focus on:
            1. Creating a powerful but BRIEF professional summary (max 2-3 lines)
            2. Limiting work experience to 3-4 most relevant positions with 2-3 bullet points each
            3. Using concise language and removing unnecessary words
            4. Quantifying achievements with metrics where possible
            5. Using action verbs and targeted keywords from the job description
            6. Keeping all content highly relevant to the target position
            
            Make sure the final resume is compact enough to fit on a single page.
            """,
            agent=resume_expert,
            expected_output="""Complete content for each resume section, including:
            - Brief professional summary (2-3 lines)
            - Work experience with 2-3 bullet points per position
            - Education details (degree, institution, year only)
            - Skills section (relevant skills only)
            - Relevant projects with brief descriptions
            - Key achievements section
            All content should be compact and optimized for a single-page resume.
            """,
            dependencies=[analyze_job]
        )
        
        # Task 3: Format and Structure Resume
        format_resume = Task(
            description="""Create a properly structured and formatted resume using the content provided.
            
            Follow these ATS-friendly formatting guidelines:
            1. Use a clean, simple structure that can be easily parsed by ATS
            2. Include clear section headers (Summary, Experience, Education, Skills, Projects, etc.)
            3. Use a chronological or hybrid format depending on the candidate's experience
            4. Ensure proper spacing and organization
            5. Include all required contact information
            6. Format the resume in a way that it can be presented as clean HTML/markdown
            
            Deliver a complete, formatted resume that is both ATS-friendly and visually appealing to human recruiters.
            """,
            agent=resume_formatter,
            expected_output="""A complete, formatted resume with all sections properly organized, including:
            - Contact information
            - Professional summary
            - Work experience
            - Education
            - Skills
            - Projects
            - Achievements
            
            The resume should be provided in a clean, structured format that can be easily rendered in HTML or markdown.
            """,
            dependencies=[tailor_resume]
        )
        
        return [analyze_job, tailor_resume, format_resume]
    
    def build_resume(self, user_profile, job_description, projects, achievements):
        """Main function to build a resume"""
        
        # Create agents and tasks
        agents = self.create_agents()
        tasks = self.create_tasks(agents, user_profile, job_description, projects, achievements)
        
        # Create and run the crew
        crew = Crew(
            agents=agents,
            tasks=tasks,
            verbose=True,
            process=Process.sequential
        )
        
        result = crew.kickoff()
        
        # Extract and clean up the final resume
        final_resume = self._extract_resume_from_result(result)
        
        return final_resume
    
    def _extract_resume_from_result(self, result):
        """Extract and clean up the final resume from the crew result"""
        # Check if the result is a CrewOutput object
        if hasattr(result, 'final_output'):
            # Extract the final output from the CrewOutput object
            result_text = result.final_output
        elif hasattr(result, 'raw_output'):
            # Alternative attribute name
            result_text = result.raw_output
        elif hasattr(result, '__str__'):
            # If it has a string representation, use that
            result_text = str(result)
        else:
            # Fallback
            raise ValueError("Could not extract resume text from crew result")
        
        # Basic cleaning - this might need to be enhanced based on actual output
        cleaned_result = result_text
        
        # Remove any markdown code block markers if present
        cleaned_result = re.sub(r'```(?:markdown|md|html)?\n', '', cleaned_result)
        cleaned_result = re.sub(r'```', '', cleaned_result)
        
        # Remove any agent commentary that might be present
        # This is a simple approach and might need refinement based on actual output patterns
        if "# Resume" in cleaned_result:
            cleaned_result = cleaned_result[cleaned_result.find("# Resume"):]
        
        return cleaned_result