# resume_builder_agent.py
from crewai import Agent, Task, Crew, Process
import os
from crewai import LLM
import json
import re
from utils.input import DateTimeEncoder # cls=DateTimeEncoder
from Resume.latex_formatter import LaTeXResumeFormatter
from Resume.pdf_converter import LaTeXPDFConverter

class ResumeBuilderCrew:
    def __init__(self, api_key):
        """Initialize the Resume Builder Crew with API key"""
        self.llm = LLM(
            model="gemini/gemini-1.5-flash",
            temperature=0.7,
            api_key=api_key
        )
        self.latex_formatter = LaTeXResumeFormatter()
        self.pdf_converter = LaTeXPDFConverter()
    
    def create_agents(self):
        """Create the agents for the resume building process"""
        
        # Resume Expert Agent
        resume_expert = Agent(
            role="ATS Resume Expert",
            goal="Create concise, single-page ATS-friendly resumes that maximize interview callback rates",
            backstory="""You are a highly experienced resume writer with 15+ years of experience
            helping candidates get past Applicant Tracking Systems (ATS) and land interviews.
            You specialize in creating powerful one-page resumes that use precise language and 
            strategic formatting to highlight achievements and skills in limited space. 
            You know exactly how to optimize resumes for relevant keywords, structure them properly,
            and emphasize the most relevant experience, even when working with limited information.""",
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
            qualifications, and even the hidden priorities that aren't explicitly stated. You have a
            talent for identifying the 5-7 most important skills and qualifications that will make a 
            candidate stand out, as well as the keywords that will help a resume pass ATS screening.
            Your analysis provides the foundation for creating highly targeted, effective resumes.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=False
        )
        
        # Resume Formatter Agent
        resume_formatter = Agent(
            role="LaTeX Resume Formatter",
            goal="Create professionally formatted LaTeX resumes that are both ATS-friendly and visually appealing",
            backstory="""You are a LaTeX expert specialized in resume formatting. You know how to
            structure content for maximum readability while ensuring compatibility with ATS systems.
            You understand how to balance whitespace, select appropriate fonts, and organize sections
            to create a resume that is both machine-readable and aesthetically pleasing. You have
            extensive experience with one-page resume formats and know exactly how to arrange content
            to fit everything important onto a single page without making it look crowded or compromising
            on readability.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=False
        )
        
        return [resume_expert, job_analyzer, resume_formatter]
    
    def create_tasks(self, agents, user_profile, job_description, projects, achievements):
        """Create tasks for the resume building process with improved prompts for concise one-page resumes"""
        
        # Unpack agents
        resume_expert, job_analyzer, resume_formatter = agents
        
        # Task 1: Analyze Job Description
        analyze_job = Task(
            description=f"""Analyze the job description carefully to extract the most critical elements that will help create a highly targeted one-page resume:
            
            1. Required skills and qualifications (prioritize top 5-7)
            2. Key responsibilities that align with candidate's experience
            3. Industry-specific keywords and phrases (focus on high impact terms)
            4. Soft skills that appear important for the role
            5. Company values that can be reflected in the resume
            
            Job Description:
            {job_description}
            
            Focus on extracting insights that will help create a resume that passes ATS scanning while being concise enough to fit on a single page. 
            Identify patterns in the job description that reveal what the employer values most.
            """,
            agent=job_analyzer,
            expected_output="""A focused analysis with:
            - Top 5-7 required technical skills in order of importance
            - Top 3-5 required soft skills
            - Key responsibilities that best match candidate's background
            - 10-15 high-impact keywords for ATS optimization
            - Brief insights on company values and culture fit indicators
            """
        )
        
        # Task 2: Tailor Resume Content
        tailor_resume = Task(
            description=f"""Create highly targeted, concise content for a single-page ATS-friendly resume following LaTeX formatting guidelines. 
            
            Candidate Profile:
            {json.dumps(user_profile, indent=2, cls=DateTimeEncoder)}
            
            Projects:
            {projects}
            
            Achievements:
            {achievements}
            
            Guidelines for one-page LaTeX resume:
            1. Create a powerful 2-3 line professional summary highlighting the most relevant experience and skills
            2. For each experience entry, include 2-3 high-impact bullet points that:
               - Start with strong action verbs
               - Include metrics and quantifiable achievements when possible
               - Incorporate keywords from the job analysis
               - Use concise language (aim for 1-2 lines per bullet)
            3. For projects, focus on 1-2 that best demonstrate relevant skills with 2-3 bullet points each
            4. Group technical skills into 2-3 logical categories
            5. Limit education details to degree, institution, location, and graduation year
            
            Even if the candidate has limited information in some areas, develop compelling, achievement-oriented content that elevates their profile.
            Remember that space is extremely limited - focus on quality over quantity for all sections.
            """,
            agent=resume_expert,
            expected_output="""Concise, impactful content for a single-page resume including:
            - Brief professional summary (2-3 lines)
            - Work experience with 2-3 high-impact bullet points per role
            - Concise education section
            - Categorized skills section
            - 1-2 most relevant projects with brief descriptions
            - Key achievements formatted as bullet points
            """,
            dependencies=[analyze_job]
        )
        
        # Task 3: Format and Structure Resume for LaTeX
        format_resume = Task(
            description="""Create a properly structured resume following the LaTeX template format provided for a clean, ATS-friendly single-page document.
            
            Follow these specific formatting guidelines:
            1. Use the exact LaTeX template structure from the example provided
            2. Ensure the entire resume fits on a single page by:
               - Using concise section headers (Education, Experience, Skills, Projects, etc.)
               - Adjusting spacing between sections to maximize space efficiency
               - Prioritizing the most relevant information
               - Using appropriate font sizes and margins
            3. Format content to be both ATS-friendly and visually appealing
            4. Include proper contact information in the header
            5. Ensure consistent styling throughout the document
            
            The final output should be ready-to-compile LaTeX code that produces a professional, single-page resume.
            
            If any section needs to be shortened to fit on one page, prioritize based on relevance to the target position.
            """,
            agent=resume_formatter,
            expected_output="""Complete, properly formatted LaTeX code that:
            - Strictly follows the template structure
            - Fits all content on a single page

            - Includes all required sections properly organized
            - Is ready for immediate compilation
            - Maintains ATS-friendliness while having visual appeal
            """,
            dependencies=[tailor_resume]
        )
        
        return [analyze_job, tailor_resume, format_resume]
    
    def build_resume(self, user_profile, job_description, projects="", achievements=""):
        """
        Run the resume building process from start to finish
        
        Args:
            user_profile (dict): Dictionary containing user profile information
            job_description (str): The job description text
            projects (str): Description of user's projects
            achievements (str): User's achievements
            
        Returns:
            dict: Dictionary containing the LaTeX code and PDF binary
        """
        # Create the agents
        agents = self.create_agents()
        
        # Create the tasks
        tasks = self.create_tasks(agents, user_profile, job_description, projects, achievements)
        
        # Create and run the crew
        crew = Crew(
            agents=agents,
            tasks=tasks,
            verbose=True,
            process=Process.sequential
        )
        
        # Run the crew to get the result
        crew_result = crew.kickoff()
        
        # Extract LaTeX code from the result
        latex_code = self._extract_latex_code(crew_result)
        
        # Format the LaTeX code with proper template and styling
        formatted_latex = self.latex_formatter.format(latex_code, user_profile)
        
        # Try to convert to PDF, but handle if it fails
        try:
            pdf_binary, message, _ = self.pdf_converter.convert_latex_to_pdf(formatted_latex)
            return {
                "latex_code": formatted_latex,
                "pdf_binary": pdf_binary,
                "message": message
            }
        except Exception as e:
            return {
                "latex_code": formatted_latex,
                "pdf_binary": None,
                "message": str(e)
            }
    def _extract_latex_code(self, crew_result):
        """
        Extract the LaTeX code from the crew result
        
        Args:
            crew_result (str): The result from the crew execution
            
        Returns:
            str: Extracted LaTeX code
        """
        # Pattern to match LaTeX code blocks in the result
        latex_pattern = r'```(?:latex)?\s*(.*?)```'
        
        # Find all matches
        matches = re.findall(latex_pattern, crew_result, re.DOTALL)
        
        if matches:
            # Return the last LaTeX code block found
            return matches[-1].strip()
        else:
            # If no LaTeX code block is found, return the raw result
            # This assumes the entire result might be LaTeX code without code block formatting
            return crew_result.strip()