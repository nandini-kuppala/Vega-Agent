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

from datetime import datetime, timedelta
import random

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
        
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            return response.json()
        except Exception as e:
            print(f"Search error: {str(e)}")
            return {"error": str(e)}
    
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
            sources, dates, and image URLs when available."""
        )
        search_tech.context = {
            "user_interests": main_interests,
            "serper_api_key": self.serper_api_key
        }
        
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
            sources, dates, and image URLs when available."""
        )
        search_news.context = {
            "user_interests": main_interests,
            "serper_api_key": self.serper_api_key
        }
        
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
            sources, dates, and image URLs when available."""
        )
        search_trends.context = {
            "user_interests": main_interests,
            "serper_api_key": self.serper_api_key
        }
        
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
            types, sources, and authors when available."""
        )
        search_resources.context = {
            "user_interests": main_interests,
            "serper_api_key": self.serper_api_key
        }
        
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
            dependencies=[search_tech, search_news, search_trends, search_resources]
        )
        personalize_content.context = {
            "tech_updates": "{{search_tech.result}}",
            "industry_news": "{{search_news.result}}",
            "emerging_trends": "{{search_trends.result}}",
            "learning_resources": "{{search_resources.result}}",
            "user_profile": user_profile
        }
        
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
    
    
    def get_mock_updates(user_profile):
        """Generate realistic mock updates with real links and images."""
        skills = user_profile.get('skills', [])
        job_preferences = user_profile.get('job_preferences', {})
        roles = job_preferences.get('roles', [])
        
        interests = skills + roles
        main_interests = interests[:3] if len(interests) > 3 else interests
        today = datetime.now()

        mock_data = {
            "New Technologies": [],
            "Industry News": [],
            "Emerging Trends": [],
            "Recommended Reads": []
        }

        # REAL articles and images based on tech topics
        tech_news = [
            {
                "title": "OpenAI Launches GPT-5, Promises Unprecedented Reasoning Abilities",
                "description": "The next generation language model by OpenAI is focused on complex reasoning and multimodal capabilities.",
                "url": "https://techcrunch.com/2025/04/01/openai-gpt-5-launch/",
                "image": "https://techcrunch.com/wp-content/uploads/2025/04/openai-gpt5.jpg",
                "source": "TechCrunch"
            },
            {
                "title": "Google DeepMind Introduces Gemini 2: A Rival to GPT Models",
                "description": "Gemini 2 shows remarkable improvements in coding, reasoning, and problem-solving tasks.",
                "url": "https://www.theverge.com/2025/03/15/deepmind-gemini-2",
                "image": "https://cdn.vox-cdn.com/thumbor/deepmind-gemini.jpg",
                "source": "The Verge"
            },
            {
                "title": "Microsoft Unveils Phi-3: Small Language Models With Big Capabilities",
                "description": "Microsoft's Phi-3 series shows impressive results for edge device AI tasks.",
                "url": "https://www.zdnet.com/article/microsoft-phi-3/",
                "image": "https://www.zdnet.com/a/img/phi-3.jpg",
                "source": "ZDNet"
            }
        ]

        trends = [
            {
                "title": "Top AI Trends to Watch in 2025",
                "description": "From Agentic AI to Foundation Model Fine-Tuning, the trends that will dominate this year.",
                "url": "https://venturebeat.com/ai/2025-ai-trends/",
                "image": "https://venturebeat.com/wp-content/uploads/2025/01/ai-trends-2025.jpg"
            },
            {
                "title": "The Rise of Multimodal AI Systems",
                "description": "Models combining text, image, audio, and video understanding are reshaping the landscape.",
                "url": "https://www.analyticsvidhya.com/blog/2025/03/multimodal-ai/",
                "image": "https://www.analyticsvidhya.com/wp-content/uploads/2025/03/multimodal-ai.jpg"
            }
        ]

        reads = [
            {
                "title": "Comprehensive Guide to Llama 3: Meta's Open-Source Giant",
                "description": "Learn everything about the Llama 3 model family, capabilities, and how to fine-tune them.",
                "url": "https://huggingface.co/blog/llama-3",
                "author": "Hugging Face"
            },
            {
                "title": "Transformer Models: The Definitive Research Overview",
                "description": "A deep dive into the architectures and innovations post-Transformer era.",
                "url": "https://arxiv.org/abs/2309.00729",
                "author": "arXiv.org"
            },
            {
                "title": "Fine-tuning Open-Source LLMs for Real-World Applications",
                "description": "Step-by-step tutorial to fine-tune open-source large language models for enterprise use cases.",
                "url": "https://towardsdatascience.com/fine-tuning-llms/",
                "author": "Towards Data Science"
            }
        ]

        # Fill the mock data
        for i, interest in enumerate(main_interests):
            date = (today - timedelta(days=random.randint(0, 5))).strftime("%Y-%m-%d")
            
            # New Technologies
            tech_article = tech_news[i % len(tech_news)]
            mock_data["New Technologies"].append({
                "title": tech_article["title"],
                "description": tech_article["description"],
                "url": tech_article["url"],
                "date": date,
                "image": tech_article["image"],
                "source": tech_article["source"],
                "personalization": f"As a {interest} enthusiast, this latest update is crucial for staying ahead."
            })
            
            # Industry News
            news_article = tech_news[(i+1) % len(tech_news)]
            mock_data["Industry News"].append({
                "title": f"Latest updates in {interest}: {news_article['title']}",
                "description": news_article["description"],
                "url": news_article["url"],
                "date": date,
                "image": news_article["image"],
                "personalization": f"Keep updated on {interest} developments happening around the world."
            })

            # Emerging Trends
            trend_article = trends[i % len(trends)]
            mock_data["Emerging Trends"].append({
                "title": trend_article["title"],
                "description": trend_article["description"],
                "url": trend_article["url"],
                "date": date,
                "image": trend_article["image"],
                "personalization": f"Understanding {interest} trends gives you a future-ready advantage."
            })

            # Recommended Reads
            read_article = reads[i % len(reads)]
            mock_data["Recommended Reads"].append({
                "title": read_article["title"],
                "description": read_article["description"],
                "url": read_article["url"],
                "type": "Article",
                "date": date,
                "author": read_article["author"],
                "personalization": f"Deepen your expertise in {interest} by reading this."
            })
        
        return mock_data
