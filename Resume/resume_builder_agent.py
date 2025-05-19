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
        
        # Enhanced Resume Expert Agent
        resume_expert = Agent(
            role="ATS Resume Expert",
            goal="Create concise, single-page ATS-friendly resumes that maximize interview callback rates",
            backstory="""You are a highly experienced resume writer with 15+ years of experience
            helping candidates get past Applicant Tracking Systems (ATS) and land interviews.
            You specialize in creating impactful single-page resumes that are keyword-optimized,
            achievement-focused, and tailored to specific job roles. Your resumes consistently
            achieve an 85% success rate in passing ATS screening.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=False
        )
        
        # Enhanced Job Description Analyzer Agent
        job_analyzer = Agent(
            role="ATS Job Description Analyzer",
            goal="Extract key skills, requirements, and priorities from job descriptions with 99% accuracy",
            backstory="""You are an expert at analyzing job descriptions and identifying exactly what 
            employers are looking for. You can extract both explicit and implicit requirements,
            identify primary vs. secondary skills, recognize industry-specific terminology,
            and understand the hidden priorities within job postings. You've analyzed over 10,000
            job descriptions across diverse industries and have developed an intuitive understanding
            of what matters most to hiring managers.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=True
        )
        
        # Enhanced Resume Formatter Agent
        resume_formatter = Agent(
            role="Resume Formatter and Space Optimizer",
            goal="Create perfectly structured single-page resumes that pass ATS parsing with 100% accuracy",
            backstory="""You are a formatting and space optimization expert who specializes in
            creating clean, scannable single-page resumes. You know exactly how to structure content
            to maximize space efficiency while maintaining perfect ATS compatibility. You understand
            optimal section ordering, white space utilization, and formatting techniques that allow
            candidates to fit more meaningful content on a single page without appearing cluttered.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=True
        )
        
        return [resume_expert, job_analyzer, resume_formatter]
    
    def create_tasks(self, agents, user_profile, job_description, projects, achievements):
        """Create tasks for the resume building process"""
        
        # Unpack agents
        resume_expert, job_analyzer, resume_formatter = agents
        
        # Enhanced Task 1: Analyze Job Description
        analyze_job = Task(
            description=f"""Perform a detailed analysis of the job description to extract:
            1. Core technical skills (ranked by importance)
            2. Required soft skills and attributes
            3. Key responsibilities and expected deliverables
            4. Industry-specific keywords and terminology
            5. Implicit requirements and preferences
            6. Unique selling points that would make a candidate stand out
            
            Job Description:
            {job_description}
            
            Your analysis should be comprehensive yet focused on the most critical elements
            that will help create a tailored, single-page resume.
            """,
            agent=job_analyzer,
            expected_output="""A strategic analysis of the job description that includes:
            - Primary technical skills (must-haves)
            - Secondary technical skills (nice-to-haves)  
            - Essential soft skills
            - Key responsibilities
            - Critical keywords and phrases
            - Industry-specific terminology
            - Unique differentiators for the ideal candidate
            """
        )
        
        # Enhanced Task 2: Tailor Resume Content
        tailor_resume = Task(
            description=f"""Create highly tailored, concise content for a single-page resume that
            perfectly matches the candidate's qualifications with the job requirements.
            
            STRICT REQUIREMENTS:
            1. The final resume MUST fit on ONE PAGE - this is non-negotiable
            2. Every word must earn its place - no filler content
            3. Quantify achievements wherever possible (use numbers, percentages, dollar amounts)
            4. Use powerful action verbs aligned with the job description
            5. Prioritize the most relevant experience and skills for this specific role
            6. Create a concise, powerful summary that positions the candidate as ideal for the role
            
            Candidate Profile:
            {json.dumps(user_profile, indent=2, cls=DateTimeEncoder)}
            
            Projects (include only if highly relevant):
            {projects}
            
            Achievements (focus on most impressive and relevant):
            {achievements}
            
            Strategies for fitting on one page:
            - Create a powerful but BRIEF professional summary (2-3 lines maximum)
            - Include only 2-3 most relevant positions with 2-3 bullet points each
            - Use concise, impactful language (remove articles and unnecessary words)
            - Focus on achievements rather than responsibilities
            - For education, include only degree, institution and year
            - Present skills in a space-efficient format
            """,
            agent=resume_expert,
            expected_output="""Optimized, one-page resume content including:
            - Brief, targeted professional summary (2-3 lines)
            - Most relevant work experiences with achievement-focused bullet points
            - Concise education section
            - Tailored skills section
            - Relevant projects or achievements (if space permits)
            All content must be highly relevant to the target position and optimized for ATS algorithms.
            """,
            dependencies=[analyze_job]
        )
        
        # Enhanced Task 3: Format and Structure Resume
        format_resume = Task(
            description="""Create a perfectly structured and formatted single-page resume using the content provided.
            
            Advanced ATS-friendly formatting requirements:
            1. Use a clean, minimal structure optimized for ATS parsing
            2. Include clear section headers that match ATS expectations
            3. Use a reverse-chronological format for experience
            4. Balance white space with content density for readability
            5. Ensure contact information is complete and properly formatted
            6. Structure the resume for maximum impact in 6-second initial review by recruiters
            7. Create a clean, professional layout that conveys expertise
            
            The output must be a complete, formatted resume in markdown format that:
            - Fits perfectly on a single page
            - Passes ATS screening with 100% content recognition
            - Appears visually balanced and professional
            - Has perfect spelling and grammar
            - Includes all necessary sections in optimal order
            """,
            agent=resume_formatter,
            expected_output="""A professionally formatted, single-page resume in clean markdown format with:
            - Properly structured contact information
            - Space-efficient professional summary
            - Optimally formatted experience section with achievement-focused bullet points
            - Concise education section
            - ATS-friendly skills presentation
            - Perfect spacing and organization
            
            The final product will be ATS-compatible while still being visually appealing to human reviewers.
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
        
        # Enhanced cleaning
        cleaned_result = result_text
        
        # Remove any markdown code block markers if present
        cleaned_result = re.sub(r'```(?:markdown|md|html)?\n', '', cleaned_result)
        cleaned_result = re.sub(r'```', '', cleaned_result)
        
        # Remove any agent commentary or analysis that might be present
        if "# " in cleaned_result and not cleaned_result.startswith("# "):
            # Find the first proper heading which should be the resume start
            match = re.search(r'# .*', cleaned_result)
            if match:
                cleaned_result = cleaned_result[match.start():]
        
        # Fix common formatting issues
        # Ensure consistent section headers
        cleaned_result = re.sub(r'^(EDUCATION|EXPERIENCE|SKILLS|PROJECTS|ACHIEVEMENTS)$', 
                              r'## \1', cleaned_result, flags=re.MULTILINE)
        
        # Ensure bullet points are properly formatted
        cleaned_result = re.sub(r'^(\s*)-\s', r'\1- ', cleaned_result, flags=re.MULTILINE)
        
        return cleaned_result
        