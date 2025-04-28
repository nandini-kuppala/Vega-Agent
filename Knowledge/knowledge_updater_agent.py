from crewai import Agent, Task, Crew, Process
import os
from crewai import LLM
import json
import re
from datetime import datetime
from typing import Dict, List, Any

class KnowledgeUpdaterCrew:
    def __init__(self, api_key):
        """Initialize the Knowledge Updater Crew with API key"""
        self.llm = LLM(
            model="gemini/gemini-1.5-flash",
            temperature=0.2,
            api_key=api_key
        )
    
    def create_agents(self):
        """Create the agents for the knowledge update process"""
        
        # Technology Scout Agent
        tech_scout = Agent(
            role="Technology Scout",
            goal="Discover the latest technology updates and innovations relevant to the candidate",
            backstory="""You are a technology scout with an encyclopedic knowledge of the latest 
            tools, frameworks, libraries, and technological developments. You stay up-to-date with 
            all emerging technologies across various domains and have a talent for identifying 
            which technologies are most relevant to specific skill sets and industries.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=False
        )
        
        # Industry Analyst Agent
        industry_analyst = Agent(
            role="Industry Analyst",
            goal="Provide industry-specific news and insights",
            backstory="""You are a seasoned industry analyst who monitors market trends, 
            company movements, and industry shifts. You have deep knowledge of multiple 
            sectors including tech, healthcare, finance, and more. You understand industry 
            challenges, opportunities, and can contextualize news in terms of their 
            significance for professionals in that industry.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=True
        )
        
        # Trends Researcher Agent
        trends_researcher = Agent(
            role="Trends Researcher",
            goal="Identify emerging trends and future directions",
            backstory="""You are an expert at spotting patterns and forecasting future directions.
            You analyze multiple data points to identify emerging trends that will affect 
            various industries and skill domains. You're particularly good at connecting 
            seemingly unrelated developments to identify larger movements in the professional
            landscape.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=True
        )
        
        # Content Curator Agent
        content_curator = Agent(
            role="Content Curator",
            goal="Select and recommend valuable content for professional development",
            backstory="""You are a talented content curator with a knack for finding the most 
            valuable articles, videos, courses, and resources on any topic. You understand what 
            makes content useful for professionals at different stages of their careers and
            can match learning resources to specific skill development needs.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=True
        )
        
        return [tech_scout, industry_analyst, trends_researcher, content_curator]
    
    def create_tasks(self, agents, candidate_profile):
        """Create tasks for the knowledge update process"""
        
        # Unpack agents
        tech_scout, industry_analyst, trends_researcher, content_curator = agents
        
        # Extract profile information
        skills = candidate_profile.get('skills', [])
        industry = candidate_profile.get('industry', '')
        interests = candidate_profile.get('interests', [])
        
        today = datetime.now().strftime("%B %d, %Y")
        
        # Task 1: Generate Technology Updates
        tech_updates_task = Task(
            description=f"""Based on the candidate's profile, generate 3-5 significant technology 
            updates that would be most relevant to them as of {today}.
            
            Candidate Skills: {', '.join(skills) if isinstance(skills, list) else skills}
            Industry: {industry}
            Interests: {', '.join(interests) if isinstance(interests, list) else interests}
            
            For each technology update, provide:
            1. A concise headline
            2. A brief description (2-3 sentences)
            3. Why it's relevant to the candidate's profile
            4. A potential impact on their professional growth
            
            The updates should be current and relevant to the candidate's background.
            """,
            agent=tech_scout,
            expected_output="""A structured list of 3-5 technology updates with headlines, 
            descriptions, relevance explanations, and potential impacts."""
        )
        
        # Task 2: Generate Industry News
        industry_news_task = Task(
            description=f"""Based on the candidate's profile, generate 3-4 important industry news 
            items that would be most relevant to them as of {today}.
            
            Candidate Skills: {', '.join(skills) if isinstance(skills, list) else skills}
            Industry: {industry}
            Interests: {', '.join(interests) if isinstance(interests, list) else interests}
            
            For each news item, provide:
            1. A concise headline
            2. A brief description (2-3 sentences)
            3. Why it matters for professionals in this field
            
            The news should be current and focus on major developments in the candidate's industry.
            """,
            agent=industry_analyst,
            expected_output="""A structured list of 3-4 industry news items with headlines, 
            descriptions, and significance explanations."""
        )
        
        # Task 3: Identify Emerging Trends
        trends_task = Task(
            description=f"""Based on the candidate's profile, identify 2-3 emerging trends 
            that could impact their career trajectory or should be on their radar as of {today}.
            
            Candidate Skills: {', '.join(skills) if isinstance(skills, list) else skills}
            Industry: {industry}
            Interests: {', '.join(interests) if isinstance(interests, list) else interests}
            
            For each trend, provide:
            1. A name or title for the trend
            2. A description of the trend and its current state
            3. How this trend might evolve in the next 6-12 months
            4. Why the candidate should pay attention to this trend
            
            Focus on trends that are not yet mainstream but are gaining momentum.
            """,
            agent=trends_researcher,
            expected_output="""A structured list of 2-3 emerging trends with names, 
            descriptions, future outlook, and relevance explanations."""
        )
        
        # Task 4: Recommend Learning Resources
        resources_task = Task(
            description=f"""Based on the candidate's profile and the identified technology 
            updates, industry news, and emerging trends, recommend 3-4 high-quality resources 
            for further learning.
            
            Candidate Skills: {', '.join(skills) if isinstance(skills, list) else skills}
            Industry: {industry}
            Interests: {', '.join(interests) if isinstance(interests, list) else interests}
            
            For each resource, provide:
            1. Title of the resource
            2. Type (article, video, course, etc.)
            3. A brief description of what the candidate would learn
            4. Why this resource is valuable for their professional development
            
            Focus on resources that would help the candidate stay ahead in their field or 
            develop skills that will be increasingly valuable based on the identified trends.
            """,
            agent=content_curator,
            expected_output="""A structured list of 3-4 learning resources with titles, 
            types, descriptions, and value explanations.""",
            context={
                "tech_updates": "{{tech_updates_task.result}}",
                "industry_news": "{{industry_news_task.result}}",
                "emerging_trends": "{{trends_task.result}}"
            },
            dependencies=[tech_updates_task, industry_news_task, trends_task]
        )
        
        return [tech_updates_task, industry_news_task, trends_task, resources_task]
    
    def generate_knowledge_update(self, candidate_profile):
        """Main function to generate knowledge updates for a candidate"""
        
        # Create agents and tasks
        agents = self.create_agents()
        tasks = self.create_tasks(agents, candidate_profile)
        
        # Create and run the crew
        crew = Crew(
            agents=agents,
            tasks=tasks,
            verbose=True,
            process=Process.sequential
        )
        
        result = crew.kickoff()
        
        # Process and structure the results
        structured_update = self._structure_knowledge_update(result)
        
        return structured_update
    
    def _structure_knowledge_update(self, result):
        """Process and structure the knowledge update results"""
        # Initialize structured output
        knowledge_update = {
            "date": datetime.now().strftime("%B %d, %Y"),
            "sections": {
                "tech_updates": [],
                "industry_news": [],
                "emerging_trends": [],
                "recommended_reads": []
            }
        }
        
        # Parse the result text to extract each section
        # This is a simplified approach; in a real system you might use 
        # more robust parsing or have the agents return structured data
        
        tech_section = self._extract_section(result, "technology updates", "industry news")
        if tech_section:
            knowledge_update["sections"]["tech_updates"] = self._parse_tech_updates(tech_section)
        
        news_section = self._extract_section(result, "industry news", "emerging trends")
        if news_section:
            knowledge_update["sections"]["industry_news"] = self._parse_industry_news(news_section)
        
        trends_section = self._extract_section(result, "emerging trends", "learning resources")
        if trends_section:
            knowledge_update["sections"]["emerging_trends"] = self._parse_trends(trends_section)
        
        resources_section = self._extract_section(result, "learning resources", None)
        if resources_section:
            knowledge_update["sections"]["recommended_reads"] = self._parse_resources(resources_section)
        
        return knowledge_update
    
    def _extract_section(self, text, start_marker, end_marker=None):
        """Extract a section from text based on markers"""
        # Find the section in the text (case insensitive)
        pattern = r'(?i)(?:#+\s*|^).*' + re.escape(start_marker) + r'.*?(?=(?:#+\s*|^).*' 
        if end_marker:
            pattern += re.escape(end_marker)
        else:
            pattern += r'$)'
        
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(0)
        return ""
    
    def _parse_tech_updates(self, section):
        """Parse technology updates from the section text"""
        # Extract items that look like update entries
        # This is a simplified parser; you might need to adjust based on actual output format
        items = []
        
        # Look for numbered items or headings
        pattern = r'(?:^|\n)(?:##+\s*|\d+\.\s*|\*\s*)(.*?)(?=(?:^|\n)(?:##+\s*|\d+\.\s*|\*\s*)|$)'
        matches = re.finditer(pattern, section, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            item_text = match.group(1).strip()
            if item_text:
                # Try to extract headline and description
                lines = item_text.split('\n', 1)
                headline = lines[0].strip()
                description = lines[1].strip() if len(lines) > 1 else ""
                
                items.append({
                    "headline": headline,
                    "description": description
                })
        
        return items
    
    def _parse_industry_news(self, section):
        """Parse industry news from the section text"""
        # Similar approach to tech updates
        return self._parse_tech_updates(section)  # Reuse the same parser for now
    
    def _parse_trends(self, section):
        """Parse emerging trends from the section text"""
        # Similar approach to tech updates
        return self._parse_tech_updates(section)  # Reuse the same parser for now
    
    def _parse_resources(self, section):
        """Parse recommended resources from the section text"""
        # Similar approach to tech updates
        return self._parse_tech_updates(section)  # Reuse the same parser for now