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
            model="gemini/gemini-1.5-flash",
            temperature=0.5,
            api_key=api_key
        )
    
    def create_agents(self):
        """Create the agents for the enhanced resume building process"""
        
        # Industry Research Agent
        industry_researcher = Agent(
            role="Industry Research Specialist",
            goal="Research industry standards, trending skills, and specific employer requirements",
            backstory="""You are an industry intelligence expert with deep knowledge of current market trends,
            employer preferences, and hiring patterns across various sectors. You can quickly identify which skills,
            experiences, and qualifications are most valued in specific industries and roles. Your research ensures
            that resumes are aligned with current market expectations and contain the most relevant and impressive
            information for the target position.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=False
        )
        
        # Job Description Analyzer Agent
        job_analyzer = Agent(
            role="Job Description Analyzer",
            goal="Extract key requirements, identify hidden expectations, and map candidate qualifications to job needs",
            backstory="""You are an expert at analyzing job descriptions and identifying exactly what 
            employers are looking for. You can extract key requirements, must-have skills, preferred
            qualifications, and the hidden priorities that aren't explicitly stated. You excel at 
            reading between the lines to understand what would make a candidate truly stand out.
            You're skilled at mapping candidate qualifications to job requirements and identifying
            gaps that need to be addressed.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=True
        )
        
        # Content Enhancement Agent
        content_enhancer = Agent(
            role="Resume Content Enhancer",
            goal="Transform basic candidate information into compelling, achievement-focused content",
            backstory="""You are a master at transforming ordinary job descriptions into compelling
            achievement statements. You know how to take minimal information and expand it into
            impressive bullet points that highlight skills, results, and value added. You're an expert
            at reading between the lines of a candidate's experience to identify transferable skills
            and hidden achievements. You excel at crafting stories that demonstrate impact and showcase
            a candidate's potential even when they provide limited information.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=True
        )
        
        # ATS Optimization Agent
        ats_optimizer = Agent(
            role="ATS Optimization Specialist",
            goal="Ensure the resume passes through ATS filters and ranks highly in candidate screening",
            backstory="""You are an ATS expert who understands how these systems parse, rank, and filter resumes.
            You know exactly which keywords to include, how to format content, and what strategies to employ
            to maximize a resume's ranking in ATS systems. You understand the technical aspects of how different
            ATS platforms work, and can optimize a resume to perform well across multiple systems. You're also skilled
            at balancing ATS optimization with human readability to ensure the resume appeals to both automated systems
            and human recruiters.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=True
        )
        
        # Resume Formatter Agent
        resume_formatter = Agent(
            role="Resume Formatter & Design Expert",
            goal="Create visually appealing, properly structured resumes that are both ATS-friendly and impressive to human recruiters",
            backstory="""You are a formatting and design expert who knows exactly how to structure
            resumes for maximum impact. You understand the psychology of how recruiters scan resumes
            and know exactly how to organize information to draw attention to the most impressive elements.
            You're skilled at creating clean, modern designs that pass through ATS systems while still
            standing out visually to human readers. You know how to optimize spacing, typography, and layout
            to create a resume that looks professional and fits perfectly on a single page without appearing
            cluttered or overwhelming.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=True
        )
        
        # Final Review Agent
        final_reviewer = Agent(
            role="Final Resume Reviewer",
            goal="Provide a comprehensive final review to ensure the resume is flawless and optimized for success",
            backstory="""You are a meticulous reviewer with an eye for detail and a strategic mindset.
            You critically examine resumes from multiple perspectives: the ATS system, the recruiter who
            will scan it for 6-10 seconds, the hiring manager who needs to see relevant experience, and
            the candidate who needs to stand out from the competition. You're skilled at identifying
            weaknesses or missed opportunities and providing specific recommendations for improvement.
            You understand what makes a resume truly exceptional and know how to take it from good to outstanding.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=True
        )
        
        return [industry_researcher, job_analyzer, content_enhancer, ats_optimizer, resume_formatter, final_reviewer]
    
    def create_tasks(self, agents, user_profile, job_description, projects, achievements):
        """Create tasks for the enhanced resume building process"""
        
        # Unpack agents
        industry_researcher, job_analyzer, content_enhancer, ats_optimizer, resume_formatter, final_reviewer = agents
        
        # Task 1: Industry and Role Research
        research_task = Task(
            description=f"""Research the industry standards, trending skills, and ideal qualifications for this role.
            
            Based on available information, identify:
            1. The industry and specific sector this role belongs to
            2. Current trending skills and qualifications in this field
            3. Typical career progression paths for this role
            4. What makes candidates stand out in this particular field
            5. Relevant industry-specific terminology, tools, and technologies
            
            Job Description:
            {job_description}
            
            User Profile Overview:
            {json.dumps(user_profile, indent=2, cls=DateTimeEncoder)}
            
            Provide comprehensive insights that will help position this candidate as an ideal fit for the role.
            """,
            agent=industry_researcher,
            expected_output="""A detailed analysis of the industry standards including:
            - Industry overview and current trends
            - Most valued skills and qualifications for this specific role
            - Industry-specific terminology and technologies
            - What makes candidates stand out in this field
            - Recommendations for positioning the candidate effectively
            """
        )
        
        # Task 2: Analyze Job Description
        analyze_job = Task(
            description=f"""Perform a deep analysis of the job description to extract:
            1. Required skills, qualifications, and experience levels
            2. Preferred/desired skills and experience
            3. Key responsibilities and expected deliverables
            4. Specific technical tools, software, or methodologies mentioned
            5. Soft skills and personality traits indicated (directly or implied)
            6. Company values and culture indicators
            7. Hidden requirements and expectations not explicitly stated
            8. Priority areas (what's mentioned first or repeatedly)
            
            Job Description:
            {job_description}
            
            Industry Research:
            {{research_task.output}}
            
            Provide a comprehensive analysis that maps exactly what this employer is looking for.
            For each requirement, assign a priority level (Must-Have, Important, Nice-to-Have).
            """,
            agent=job_analyzer,
            expected_output="""A detailed analysis of the job requirements including:
            - Prioritized list of technical skills and qualifications
            - Prioritized list of soft skills and traits
            - Key responsibilities and expected results
            - Company values and culture fit indicators
            - Hidden requirements and expectations
            - Industry-specific keywords and phrases to include
            - Recommendations for areas to emphasize based on priority
            """,
            dependencies=[research_task]
        )
        
        # Task 3: Enhance and Expand Candidate Content
        enhance_content = Task(
            description=f"""Based on the job analysis and the candidate's profile, enhance and expand their information
            to create compelling, achievement-focused content that aligns with job requirements.
            
            Candidate Profile:
            {json.dumps(user_profile, indent=2, cls=DateTimeEncoder)}
            
            Projects:
            {projects}
            
            Achievements:
            {achievements}
            
            Job Analysis:
            {{analyze_job.output}}
            
            For each position and project:
            1. Transform basic descriptions into powerful achievement statements
            2. Add relevant metrics and quantifiable results (estimate reasonable metrics if not provided)
            3. Highlight skills and experiences that directly match job requirements
            4. Identify and add transferable skills that might not be obvious
            5. Incorporate relevant industry terminology and keywords
            6. Ensure each bullet point demonstrates value and impact
            7. Fill in gaps in the candidate's experience with reasonable, implied accomplishments
            
            Focus on creating content that showcases the candidate as an ideal fit for the role,
            even if their original information was limited or basic.
            """,
            agent=content_enhancer,
            expected_output="""Enhanced and expanded content including:
            - Compelling professional summary
            - Achievement-focused bullet points for each position
            - Quantified results and metrics
            - Highlighted relevant skills and experiences
            - Added transferable skills and implied accomplishments
            - Industry-specific terminology and keywords
            All content should be truthful but presented in the most impressive light possible.
            """,
            dependencies=[analyze_job]
        )
        
        # Task 4: Optimize for ATS
        optimize_ats = Task(
            description=f"""Optimize the enhanced resume content for ATS systems to ensure it passes
            through filters and ranks highly in candidate screening.
            
            Enhanced Content:
            {{enhance_content.output}}
            
            Job Analysis:
            {{analyze_job.output}}
            
            Perform the following optimizations:
            1. Incorporate all high-priority keywords from the job description
            2. Use exact terminology matches for skills, tools, and qualifications
            3. Ensure proper section headers that ATS systems recognize
            4. Balance keyword density (include keywords without keyword stuffing)
            5. Check for any critical skills or requirements that might be missing
            6. Verify that the resume structure follows ATS-friendly conventions
            7. Ensure proper handling of abbreviations, acronyms, and technical terms
            
            Provide an ATS-optimized version of the resume content that maintains readability
            and appeal for human reviewers.
            """,
            agent=ats_optimizer,
            expected_output="""ATS-optimized resume content including:
            - Strategic keyword placement
            - Proper section headers
            - Optimized skill sections
            - Balanced keyword density
            - Properly formatted technical terms and acronyms
            - Recommendations for any missing critical keywords
            """,
            dependencies=[enhance_content]
        )
        
        # Task 5: Format and Structure Resume
        format_resume = Task(
            description=f"""Create a properly structured and formatted resume using the optimized content.
            
            ATS-Optimized Content:
            {{optimize_ats.output}}
            
            Follow these formatting guidelines:
            1. Create a clean, modern design that passes ATS checks
            2. Prioritize the most impressive and relevant information visually
            3. Use strategic formatting to draw attention to key achievements
            4. Organize sections in order of importance to this specific role
            5. Ensure proper spacing and visual hierarchy
            6. Include all required contact information
            7. Format the resume to fit perfectly on a single page
            8. Ensure formatting is consistent throughout
            
            The final resume should be both ATS-friendly and visually impressive to human recruiters.
            Focus on creating a design that makes the candidate stand out while ensuring all content is
            properly parsed by ATS systems.
            """,
            agent=resume_formatter,
            expected_output="""A complete, formatted resume with:
            - Professional heading with contact information
            - Strategic ordering of sections based on relevance
            - Clean, modern design that passes ATS checks
            - Proper spacing and visual hierarchy
            - Consistent formatting throughout
            - All content fitting perfectly on a single page
            
            The resume should be provided in a clean, structured format that can be easily rendered in HTML or markdown.
            """,
            dependencies=[optimize_ats]
        )
        
        # Task 6: Final Review and Optimization
        final_review = Task(
            description=f"""Perform a comprehensive final review of the resume to ensure it is flawless
            and optimized for success.
            
            Formatted Resume:
            {{format_resume.output}}
            
            Job Analysis:
            {{analyze_job.output}}
            
            Review the resume for:
            1. Overall impact and effectiveness at showcasing the candidate
            2. Perfect alignment with job requirements
            3. Compelling narrative that tells a clear story
            4. Appropriate emphasis on most relevant skills and experiences
            5. Proper balance of technical skills and soft skills
            6. Any gaps or weaknesses that could be addressed
            7. Any final optimizations for ATS or human appeal
            8. Typos, grammatical errors, or inconsistencies
            
            Provide the final, polished resume along with 3-5 key strengths of this resume and
            why it will help the candidate get selected for this role.
            """,
            agent=final_reviewer,
            expected_output="""The resume should be provided in a clean, structured format that can be easily rendered in HTML or markdown.
            """,
            dependencies=[format_resume]
        )
        
        return [research_task, analyze_job, enhance_content, optimize_ats, format_resume, final_review]
    
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
        
        # Clean and extract the resume portion
        cleaned_result = self._clean_resume_text(result_text)
        
        return cleaned_result
    
    def _clean_resume_text(self, result_text):
        """Clean up the resume text more thoroughly"""
        # Remove any markdown code block markers
        cleaned_result = re.sub(r'```(?:markdown|md|html)?\n', '', result_text)
        cleaned_result = re.sub(r'```', '', cleaned_result)
        
        # Extract just the resume portion if there's additional commentary
        # Look for common resume section markers
        resume_sections = [
            "# RESUME", "# Resume", "# Professional Resume",
            "CONTACT INFORMATION", "PROFESSIONAL SUMMARY", "SUMMARY",
            "EXPERIENCE", "WORK EXPERIENCE", "SKILLS", "EDUCATION"
        ]
        
        # Find the start of the resume content
        resume_start = len(result_text)
        for section in resume_sections:
            pos = result_text.find(section)
            if pos != -1 and pos < resume_start:
                resume_start = pos
        
        # Find the end of the resume content (look for review sections or agent comments)
        end_markers = [
            "# Review", "# KEY STRENGTHS", "# RECOMMENDATIONS",
            "Here are the key strengths", "This resume will help the candidate"
        ]
        
        resume_end = len(result_text)
        for marker in end_markers:
            pos = result_text.find(marker, resume_start)
            if pos != -1 and pos < resume_end:
                resume_end = pos
        
        # Extract just the resume portion
        if resume_start < len(result_text):
            resume_text = result_text[resume_start:resume_end].strip()
        else:
            resume_text = cleaned_result
        
        # Remove any agent commentary that might be present
        resume_text = re.sub(r'As the Final Resume Reviewer,.*?(?=\n\n|\Z)', '', resume_text, flags=re.DOTALL)
        resume_text = re.sub(r'As the Resume Formatter,.*?(?=\n\n|\Z)', '', resume_text, flags=re.DOTALL)
        
        return resume_text.strip()