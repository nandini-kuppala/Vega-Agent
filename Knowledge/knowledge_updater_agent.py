from crewai import Agent, Task, Crew, Process
import os
from crewai import LLM
import json
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import random
from utils.input import DateTimeEncoder

class KnowledgeUpdaterCrew:
    def __init__(self, serper_api_key, gemini_api_key):
        """Initialize the Knowledge Updater Crew with API keys"""
        self.serper_api_key = serper_api_key
        self.llm = LLM(
            model="gemini/gemini-1.5-flash",
            temperature=0.7,
            api_key=gemini_api_key
        )
    
    def create_agents(self):
        """Create the agents for the knowledge updating process"""
        
        # Search Expert Agent
        search_expert = Agent(
            role="Tech Search Expert",
            goal="Find the most relevant and recent information on technology and industry trends",
            backstory="""You are an expert at finding and curating the latest technology information.
            You know exactly how to craft search queries to find the most recent and relevant information
            about emerging technologies, industry news, and research breakthroughs. You are always up-to-date
            with the latest developments in the tech world.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=False
        )
        
        # Content Analyst Agent
        content_analyst = Agent(
            role="Content Analysis Expert",
            goal="Analyze and extract key insights from tech articles and news",
            backstory="""You are skilled at analyzing technical content and extracting the most
            important information. You can identify key trends, breakthrough technologies, and
            important industry shifts from news articles, blog posts, and research papers.
            You know how to distill complex technical content into clear, concise summaries.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=True
        )
        
        # Personalization Agent
        personalization_agent = Agent(
            role="Content Personalization Expert",
            goal="Tailor technology updates to individual users based on their profile and interests",
            backstory="""You specialize in personalizing content for individuals based on their
            interests, skills, and career goals. You understand how to match technical content to
            a person's background and learning objectives. You excel at identifying which technologies,
            trends, and resources would be most valuable for a particular individual's growth.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=True
        )
        
        return [search_expert, content_analyst, personalization_agent]
    
    def perform_search(self, query):
        """Perform a search using the Serper API"""
        url = "https://google.serper.dev/search"
        
        payload = json.dumps({
            "q": query,
            "num": 5
        })
        
        headers = {
            'X-API-KEY': self.serper_api_key,
            'Content-Type': 'application/json'
        }
        
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.json()
    
    def fetch_webpage_content(self, url):
        """Fetch and parse content from a webpage"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.extract()
                
                # Extract text
                text = soup.get_text(separator='\n')
                
                # Clean up text
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                # Limit text length to avoid token limits
                return text[:5000]  # Limit to first 5000 characters
            else:
                return f"Error fetching content: Status code {response.status_code}"
        except Exception as e:
            return f"Error fetching content: {str(e)}"
    
    def create_tasks(self, agents, user_profile):
        """Create tasks for the knowledge updating process"""
        
        # Unpack agents
        search_expert, content_analyst, personalization_agent = agents
        
        # Extract key interests and skills from user profile
        skills = user_profile.get('skills', [])
        job_preferences = user_profile.get('job_preferences', {})
        roles = job_preferences.get('roles', [])
        
        # Generate search queries
        interests = skills + roles
        main_interests = ', '.join(interests[:3]) if len(interests) > 3 else ', '.join(interests)
        
        # Task 1: Search for Latest Technologies
        search_tech = Task(
            description=f"""Find the latest technology updates related to the user's background and interests.
            
            User's main interests: {main_interests}
            
            Search for:
            1. Latest advancements in {main_interests}
            2. New tools, frameworks, or platforms related to these areas
            3. Recent technological breakthroughs in these fields
            
            For each result, provide:
            - Title of the news/update
            - Brief description (1-2 sentences)
            - Source URL
            - Date published (if available)
            - Image URL (if available)
            
            Perform at least 3 different searches to get comprehensive results.
            """,
            agent=search_expert,
            expected_output="""A structured list of technology updates with titles, descriptions, 
            sources, dates, and image URLs when available.""",
            context={
                "user_interests": main_interests,
                "serper_api_key": self.serper_api_key,
                "search_function": self.perform_search
            }
        )
        
        # Task 2: Search for Industry News
        search_news = Task(
            description=f"""Find recent industry news related to the user's background and interests.
            
            User's main interests: {main_interests}
            
            Search for:
            1. Recent industry developments in {main_interests}
            2. Company news related to these technologies/fields
            3. Market trends in these areas
            
            For each result, provide:
            - Title of the news
            - Brief description (1-2 sentences)
            - Source URL
            - Date published (if available)
            - Image URL (if available)
            
            Perform at least 2 different searches to get comprehensive results.
            """,
            agent=search_expert,
            expected_output="""A structured list of industry news with titles, descriptions, 
            sources, dates, and image URLs when available.""",
            context={
                "user_interests": main_interests,
                "serper_api_key": self.serper_api_key,
                "search_function": self.perform_search
            }
        )
        
        # Task 3: Search for Emerging Trends
        search_trends = Task(
            description=f"""Find emerging trends related to the user's background and interests.
            
            User's main interests: {main_interests}
            
            Search for:
            1. Emerging trends in {main_interests}
            2. Future predictions for these technologies/fields
            3. Growing adoption patterns or shifts in these areas
            
            For each result, provide:
            - Title of the trend
            - Brief description (1-2 sentences)
            - Source URL
            - Date published (if available)
            - Image URL (if available)
            
            Perform at least 2 different searches to get comprehensive results.
            """,
            agent=search_expert,
            expected_output="""A structured list of emerging trends with titles, descriptions, 
            sources, dates, and image URLs when available.""",
            context={
                "user_interests": main_interests,
                "serper_api_key": self.serper_api_key,
                "search_function": self.perform_search
            }
        )
        
        # Task 4: Find Recommended Reading Materials
        search_resources = Task(
            description=f"""Find learning resources related to the user's background and interests.
            
            User's main interests: {main_interests}
            
            Search for:
            1. Recent research papers in {main_interests}
            2. Tutorial articles or documentation for new technologies
            3. Educational videos or courses on these topics
            4. GitHub repositories or projects worth exploring
            
            For each result, provide:
            - Title of the resource
            - Brief description (1-2 sentences)
            - Type (research paper, tutorial, video, repository)
            - Source URL
            - Author/Creator (if available)
            
            Perform at least 3 different searches to get comprehensive results.
            """,
            agent=search_expert,
            expected_output="""A structured list of learning resources with titles, descriptions, 
            types, sources, and authors when available.""",
            context={
                "user_interests": main_interests,
                "serper_api_key": self.serper_api_key,
                "search_function": self.perform_search
            }
        )
        
        # Task 5: Analyze and Personalize Content
        personalize_content = Task(
            description=f"""Analyze all the gathered information and personalize it for the user based on their profile.
            
            User Profile:
            {json.dumps(user_profile, indent=2, cls=DateTimeEncoder)}
            
            For each category (technologies, news, trends, resources):
            1. Rank items by relevance to the user's specific interests and career goals
            2. Add a short personalized note for each item explaining why it's relevant to them
            3. Ensure diversity of content - don't focus only on one aspect of their interests
            4. Consider their experience level when recommending technical content
            
            Format the output as a structured JSON with separate sections for:
            - New Technologies
            - Industry News
            - Emerging Trends
            - Recommended Reads
            
            Each item should include all available metadata (title, description, URL, image, date, etc.)
            plus your added personalization notes.
            """,
            agent=personalization_agent,
            expected_output="""A JSON structure with personalized content organized into four categories:
            New Technologies, Industry News, Emerging Trends, and Recommended Reads.""",
            context={
                "tech_updates": "{{search_tech.result}}",
                "industry_news": "{{search_news.result}}",
                "emerging_trends": "{{search_trends.result}}",
                "learning_resources": "{{search_resources.result}}",
                "user_profile": user_profile
            },
            dependencies=[search_tech, search_news, search_trends, search_resources]
        )
        
        return [search_tech, search_news, search_trends, search_resources, personalize_content]
    
    def get_knowledge_updates(self, user_profile):
        """Main function to get personalized knowledge updates"""
        
        # Create agents and tasks
        agents = self.create_agents()
        tasks = self.create_tasks(agents, user_profile)
        
        # Create and run the crew
        crew = Crew(
            agents=agents,
            tasks=tasks,
            verbose=True,
            process=Process.sequential
        )
        
        try:
            result = crew.kickoff()
            
            # Extract and parse the JSON result
            # Find JSON content between triple backticks if present
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', result)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find any JSON-like structure
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    return {"error": "Could not extract JSON from result", "raw_result": result}
            
            try:
                json_result = json.loads(json_str)
                return json_result
            except json.JSONDecodeError:
                return {"error": "Invalid JSON format", "raw_result": result}
                
        except Exception as e:
            return {"error": str(e)}
    
    def get_mock_updates(self, user_profile):
        """Generate mock updates for testing without API calls"""
        # Extract key interests from profile
        skills = user_profile.get('skills', [])
        job_preferences = user_profile.get('job_preferences', {})
        roles = job_preferences.get('roles', [])
        
        interests = skills + roles
        main_interests = interests[:3] if len(interests) > 3 else interests
        
        # Current date for mock data
        today = datetime.now()
        
        # Generate mock data based on interests
        mock_data = {
            "New Technologies": [],
            "Industry News": [],
            "Emerging Trends": [],
            "Recommended Reads": []
        }
        
        # Tech updates
        tech_templates = [
            "{} Introduces Revolutionary New Features",
            "New Framework for {} Released This Week",
            "Major Breakthrough in {} Technology Announced",
            "Latest {} Tools That Are Changing Development",
            "{} 2.0: The Next Generation Is Here"
        ]
        
        for interest in main_interests:
            date = (today - timedelta(days=random.randint(0, 7))).strftime("%Y-%m-%d")
            template = random.choice(tech_templates)
            mock_data["New Technologies"].append({
                "title": template.format(interest),
                "description": f"This new development in {interest} promises to revolutionize how developers work with this technology.",
                "url": f"https://example.com/tech/{interest.lower().replace(' ', '-')}",
                "date": date,
                "image": f"https://via.placeholder.com/300x200?text={interest.replace(' ', '+')}",
                "personalization": f"As someone interested in {interest}, this will enhance your development workflow."
            })
        
        # News updates
        news_templates = [
            "Big Tech Companies Compete in {} Space",
            "Industry Leaders Announce {} Initiative",
            "Record Investment in {} Startups This Quarter",
            "The Growing Market for {} Solutions",
            "{} Conference Highlights Industry Direction"
        ]
        
        for interest in main_interests:
            date = (today - timedelta(days=random.randint(0, 10))).strftime("%Y-%m-%d")
            template = random.choice(news_templates)
            mock_data["Industry News"].append({
                "title": template.format(interest),
                "description": f"Recent developments show how {interest} is becoming increasingly important in the tech industry.",
                "url": f"https://example.com/news/{interest.lower().replace(' ', '-')}",
                "date": date,
                "image": f"https://via.placeholder.com/300x200?text={interest.replace(' ', '+')}+News",
                "personalization": f"This news is directly relevant to your interest in {interest} and could impact your career path."
            })
        
        # Emerging trends
        trend_templates = [
            "The Future of {} Is Here: What You Need to Know",
            "{} Trends That Will Dominate Next Year",
            "How {} Is Evolving: Industry Predictions",
            "The Rise of {} in Enterprise Solutions",
            "Why Everyone Is Talking About {} Now"
        ]
        
        for interest in main_interests:
            date = (today - timedelta(days=random.randint(0, 14))).strftime("%Y-%m-%d")
            template = random.choice(trend_templates)
            mock_data["Emerging Trends"].append({
                "title": template.format(interest),
                "description": f"Experts predict that {interest} will continue to grow in importance and adoption over the next year.",
                "url": f"https://example.com/trends/{interest.lower().replace(' ', '-')}",
                "date": date,
                "image": f"https://via.placeholder.com/300x200?text={interest.replace(' ', '+')}+Trends",
                "personalization": f"Staying ahead of these {interest} trends will give you a competitive advantage in your field."
            })
        
        # Reading resources
        resource_templates = [
            "Essential {} Guide for 2025",
            "Complete {} Tutorial for Advanced Developers",
            "Research Paper: Innovations in {}",
            "Learning {} Step by Step: Comprehensive Course",
            "GitHub: Best {} Projects to Learn From"
        ]
        
        for interest in main_interests:
            date = (today - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d")
            template = random.choice(resource_templates)
            resource_type = random.choice(["Article", "Tutorial", "Research Paper", "Course", "GitHub Repository"])
            mock_data["Recommended Reads"].append({
                "title": template.format(interest),
                "description": f"This {resource_type.lower()} covers everything you need to know about working with {interest}.",
                "url": f"https://example.com/learn/{interest.lower().replace(' ', '-')}",
                "type": resource_type,
                "date": date,
                "author": f"Expert in {interest}",
                "personalization": f"This resource aligns perfectly with your skill level and interest in {interest}."
            })
        
        return mock_data