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
            temperature=0.7,
            api_key=api_key
        )
    
    def create_agents(self):
        """Create the agents for the resume building process"""
        
        # Resume Expert Agent
        resume_expert = Agent(
            role="Senior ATS Resume Strategist",
            goal="Craft high-impact, ATS-optimized resumes that maximize interview callback rates and present candidates as ideal matches",
            backstory="""You are an elite resume strategist with 15+ years of experience helping candidates secure interviews at top companies.
            You've worked with hiring managers from Fortune 500 companies and understand exactly what makes a resume stand out.
            You possess extensive knowledge of ATS systems, keyword optimization, achievement-focused writing, and industry-specific terminology.
            Your expertise lies in transforming even minimal candidate information into compelling narratives that highlight potential and relevant skills.
            You're known for your ability to read between the lines of job descriptions to identify unstated preferences and priorities.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=False
        )
        
        # Job Description Analyzer Agent
        job_analyzer = Agent(
            role="Job Intelligence Specialist",
            goal="Decode job listings to extract explicit and implicit requirements, skills, keywords, and organizational priorities",
            backstory="""You are a former technical recruiter who worked at major tech companies for 10+ years.
            You've reviewed thousands of job descriptions and can immediately identify what employers are truly seeking beyond stated requirements.
            You understand the difference between must-have skills and nice-to-have qualifications, can recognize code words that signal specific priorities,
            and can extract the hidden competencies that would make a candidate successful in a role.
            You're also skilled at identifying industry-specific terminology and ATS-friendly keywords that will ensure a resume gets past initial screening.
            You can even identify company culture cues from job descriptions to help tailor personality traits in professional summaries.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=True
        )
        
        # Skills Enhancement Agent
        skills_enhancement = Agent(
            role="Skills & Achievements Amplifier",
            goal="Enhance candidate skills and experiences to align perfectly with job requirements",
            backstory="""You specialize in identifying transferable skills and relevant achievements from even minimal candidate information.
            With expertise in multiple industries, you can recognize when a project or experience demonstrates valuable skills that the candidate
            may not have explicitly mentioned. You excel at inferring technical competencies from project descriptions and translating generic 
            experiences into industry-specific accomplishments. You're also skilled at quantifying achievements and adding metrics that make
            resume bullets more impactful. Your ability to 'read between the lines' of candidate information allows you to suggest relevant
            skills they likely possess based on their background, education, and experiences.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=True
        )
        
        # Resume Formatter Agent
        resume_formatter = Agent(
            role="ATS Optimization Specialist",
            goal="Create visually appealing, perfectly structured resumes that maximize ATS scoring while impressing human reviewers",
            backstory="""You are an expert in ATS algorithms and document design who understands exactly how resume parsing systems work.
            You know which formats consistently achieve the highest ATS scores while still being visually appealing to human recruiters.
            You understand exactly how to structure content for maximum readability, which fonts and spacing optimize parsing accuracy,
            and how to position critical information where it receives the most attention. Your formatting expertise ensures resumes
            pass digital screening systems with high match percentages and then impress human reviewers with their professional presentation.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=True
        )
        
        return [resume_expert, job_analyzer, skills_enhancement, resume_formatter]
    
    def create_tasks(self, agents, user_profile, job_description, projects, achievements):
        """Create tasks for the resume building process"""
        
        # Unpack agents
        resume_expert, job_analyzer, skills_enhancement, resume_formatter = agents
        
        # Task 1: Comprehensive Job Description Analysis
        analyze_job = Task(
            description=f"""Perform a detailed analysis of the job description to extract everything that will make a candidate competitive.
            
            Job Description:
            {job_description}
            
            Analyze and extract:
            1. REQUIRED TECHNICAL SKILLS: Identify all must-have technical skills and qualifications.
            2. PREFERRED TECHNICAL SKILLS: Identify nice-to-have technical skills that would give candidates an edge.
            3. REQUIRED SOFT SKILLS: Extract key soft skills mentioned or implied in the description.
            4. KEY RESPONSIBILITIES: List the main responsibilities and what they reveal about necessary experience.
            5. INDUSTRY KEYWORDS: Identify all industry-specific terms and technical jargon that should appear in the resume.
            6. COMPANY VALUES: Identify stated or implied organizational values and cultural priorities.
            7. HIDDEN PRIORITIES: Based on language and emphasis, what unstated qualities seem most important?
            8. SENIORITY INDICATORS: Identify language that reveals the true seniority level expected.
            9. TOP 5 ATS KEYWORDS: Determine the 5 most critical keywords for ATS optimization.
            
            Also perform a frequency analysis on the job description - which terms appear most often? This indicates high priority areas.
            
            Craft your analysis to help create a resume that appears to be the perfect match for this specific role.
            """,
            agent=job_analyzer,
            expected_output="""A comprehensive analysis document with:
            1. Categorized lists of required and preferred skills (both technical and soft)
            2. Key responsibilities with analysis of what they reveal about required experience
            3. Complete list of industry-specific keywords and phrases
            4. Company culture and value indicators
            5. Hidden priorities and preferences
            6. Keyword frequency analysis
            7. The top 5 most critical ATS keywords that must appear in the resume
            """
        )
        
        # Task 2: Enhance Candidate Skills and Experience
        enhance_profile = Task(
            description=f"""Based on the job description analysis and the candidate's provided information, enhance and expand their skills and experiences.
            
            Job Analysis Results: {{analyze_job.output}}
            
            Candidate Profile:
            {json.dumps(user_profile, indent=2, cls=DateTimeEncoder)}
            
            Projects:
            {projects}
            
            Achievements:
            {achievements}
            
            Your task:
            1. IDENTIFY SKILL GAPS: Compare the candidate's profile against job requirements and identify gaps.
            2. INFER ADDITIONAL SKILLS: Based on the candidate's background, education, and projects, infer additional relevant skills they likely possess.
            3. ENHANCE PROJECT DESCRIPTIONS: Expand on provided project information to highlight relevant technical skills and achievements.
            4. QUANTIFY ACHIEVEMENTS: Add specific metrics and outcomes to make achievements more impactful.
            5. ADD RELEVANT EXPERIENCES: If the candidate's experience is limited, suggest relevant academic, volunteer, or personal projects that demonstrate key skills.
            6. TRANSLATE GENERIC SKILLS: Transform generic skills into industry-specific competencies relevant to the target role.
            
            Focus on making realistic enhancements that the candidate could credibly claim, based on their background. Create a profile that bridges any gaps between their current experience and the job requirements.
            """,
            agent=skills_enhancement,
            expected_output="""A comprehensive enhanced candidate profile including:
            1. Expanded skills list with both explicit and inferred skills
            2. Enhanced project descriptions with technical details and outcomes
            3. Quantified achievements with specific metrics
            4. Additional relevant experiences that highlight key skills
            5. Industry-specific competency translations
            All enhancements should be realistic based on the candidate's background.
            """,
            dependencies=[analyze_job]
        )
        
        # Task 3: Create Strategic Resume Content
        create_resume_content = Task(
            description=f"""Using the job analysis and enhanced candidate profile, craft strategic resume content optimized for both ATS and human reviewers.
            
            Job Analysis: {{analyze_job.output}}
            Enhanced Candidate Profile: {{enhance_profile.output}}
            
            IMPORTANT: This resume MUST fit on a single page. Be concise but impactful.
            
            Create the following content:
            
            1. ATTENTION-GRABBING HEADLINE: Create a 1-line professional headline that positions the candidate as a perfect match for the role.
            
            2. POWERFUL PROFESSIONAL SUMMARY (2-3 lines): Craft a summary that:
               - Incorporates top 3 ATS keywords
               - Highlights years of relevant experience
               - Mentions a standout achievement
               - Reflects company values/culture fit
            
            3. SKILLS SECTION: Create a skills section with:
               - Technical skills (prioritize those matching job requirements)
               - Soft skills (focus on those emphasized in job description)
               - Tools/platforms (those mentioned in job description first)
               - Format as a clean, scannable list grouped by category
            
            4. EXPERIENCE SECTION (limited to 3-4 most relevant positions):
               - Create powerful bullet points (max 3 per position)
               - Begin each with strong action verbs
               - Incorporate key ATS terms naturally
               - Follow the PAR format (Problem-Action-Result)
               - Include metrics and quantifiable achievements
               - Focus on responsibilities matching the job description
            
            5. EDUCATION & CERTIFICATIONS:
               - List relevant degrees, certifications
               - Include relevant coursework if it addresses skill gaps
            
            6. PROJECTS SECTION (if relevant):
               - Highlight 2-3 most relevant projects
               - Focus on those demonstrating key required skills
               - Include technical details that showcase expertise
            
            Use natural language that incorporates keywords without keyword stuffing. Ensure content is achievement-focused rather than just listing responsibilities.
            """,
            agent=resume_expert,
            expected_output="""Complete strategic resume content including:
            - Professional headline
            - ATS-optimized professional summary
            - Properly prioritized skills section
            - PAR-formatted experience bullets with metrics
            - Relevant education and certification details
            - Strategically selected project highlights
            
            All content should be concise enough to fit a single page while maximizing impact and ATS match score.
            """,
            dependencies=[analyze_job, enhance_profile]
        )
        
        # Task 4: Format and Structure Resume
        format_resume = Task(
            description="""Using the strategic content created, structure and format a highly effective, ATS-friendly resume.
            
            Resume Content: {create_resume_content.output}
            
            Follow these ATS optimization guidelines:
            
            1. STRUCTURE:
               - Use a proven ATS-friendly template structure
               - Include clear section headers (Summary, Experience, Skills, Education, Projects)
               - Place most important sections first (typically Experience, then Skills)
               - Create clean visual divisions between sections
            
            2. ATS OPTIMIZATION:
               - Use standard section headings that ATS systems recognize
               - Avoid tables, columns, or complex formatting that can confuse parsers
               - Ensure all text is parsable (no text in images or graphics)
               - Use standard, ATS-friendly fonts
               - Incorporate keywords naturally throughout
            
            3. DESIGN FOR HUMAN READERS:
               - Create sufficient white space for readability
               - Use strategic bold formatting for key achievements/metrics
               - Ensure consistent formatting throughout
               - Create a visually balanced layout
               - Use subtle visual elements that don't interfere with ATS parsing
            
            4. CONTACT INFORMATION:
               - Include complete contact details
               - Add LinkedIn profile if available
               - Consider adding GitHub/portfolio if relevant to role
            
            5. FORMATTING CHECKS:
               - Verify all dates are consistent in format
               - Ensure bullet points are consistent in style
               - Check for proper spacing throughout
               - Confirm content fits on a single page
            
            Create a resume that will achieve a high ATS match score while also impressing human reviewers with its professional presentation.
            """,
            agent=resume_formatter,
            expected_output="""A complete, perfectly formatted resume with:
            - Professional structure optimized for ATS parsing
            - Strategic section ordering
            - Clean, consistent formatting
            - Visual elements that enhance readability without compromising ATS compatibility
            - Proper spacing and layout to ensure single-page fit
            
            The resume should be provided in a clean, structured format that can be easily rendered in HTML or markdown.
            """,
            dependencies=[create_resume_content]
        )
        
        # Task 5: Final Review and Optimization
        final_optimization = Task(
            description="""Perform a final review and optimization of the resume to maximize its effectiveness.
            
            Formatted Resume: {format_resume.output}
            Job Analysis: {analyze_job.output}
            
            Perform these final optimizations:
            
            1. ATS KEYWORD AUDIT:
               - Verify all top ATS keywords are included
               - Check keyword placement (earlier in the resume is better)
               - Ensure natural keyword integration (no keyword stuffing)
            
            2. IMPACT ENHANCEMENT:
               - Review all achievement bullets for maximum impact
               - Verify all achievements include metrics where possible
               - Ensure strongest achievements appear first in each section
            
            3. CONTENT BALANCE CHECK:
               - Ensure appropriate space allocation across sections
               - Verify most relevant experiences receive most space
               - Check that page space reflects priorities in job description
            
            4. FINAL EDITING:
               - Ensure concise language throughout (remove unnecessary words)
               - Check for consistency in tense and formatting
               - Verify all content fits on a single page
               - Ensure no critical information is cut off
            
            5. RECOMMENDATION FOR USE:
               - Provide brief guidance on how the candidate should use this resume
               - Suggest customizations they might make for similar roles
            
            Your goal is to deliver a perfectly optimized, ready-to-submit resume that will maximize the candidate's chances of getting an interview.
            """,
            agent=resume_expert,
            expected_output="""A fully optimized final resume with:
            - Perfect keyword placement and integration
            - Maximum impact achievement statements
            - Balanced content allocation
            - Concise, powerful language throughout
            - Single-page fit with no cut-off information
            - Brief usage guidance for the candidate
            
            The final resume should represent the ideal balance of ATS optimization and human appeal.
            """,
            dependencies=[format_resume]
        )
        
        return [analyze_job, enhance_profile, create_resume_content, format_resume, final_optimization]
    
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
        
        # Enhanced cleaning process
        cleaned_result = result_text
        
        # Remove any markdown code block markers if present
        cleaned_result = re.sub(r'```(?:markdown|md|html)?\n', '', cleaned_result)
        cleaned_result = re.sub(r'```', '', cleaned_result)
        
        # Remove any agent commentary or explanations that might be present
        if "# Resume" in cleaned_result:
            cleaned_result = cleaned_result[cleaned_result.find("# Resume"):]
        elif "# RESUME" in cleaned_result:
            cleaned_result = cleaned_result[cleaned_result.find("# RESUME"):]
        
        # Remove any task completion indicators or agent signatures
        cleaned_result = re.sub(r'Task completed.*$', '', cleaned_result, flags=re.MULTILINE)
        cleaned_result = re.sub(r'Agent:.*$', '', cleaned_result, flags=re.MULTILINE)
        
        # Remove any usage guidance that might be at the end (we'll extract this separately if needed)
        if "# USAGE GUIDANCE" in cleaned_result:
            cleaned_result = cleaned_result[:cleaned_result.find("# USAGE GUIDANCE")]
        elif "# Usage Guidance" in cleaned_result:
            cleaned_result = cleaned_result[:cleaned_result.find("# Usage Guidance")]
        
        # Strip extra whitespace and normalize line endings
        cleaned_result = cleaned_result.strip()
        
        return cleaned_result