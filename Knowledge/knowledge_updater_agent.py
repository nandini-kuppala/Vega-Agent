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
    
    
    def get_mock_updates(self,user_profile):
        """Generate realistic mock updates with real links and images."""
        skills = user_profile.get('skills', [])
        job_preferences = user_profile.get('job_preferences', {})
        roles = job_preferences.get('roles', [])
        
        interests = skills + roles
        main_interests = interests
        today = datetime.now()

        mock_data = {
            "New Technologies": [],
            "Industry News": [],
            "Emerging Trends": [],
            "Recommended Reads": []
        }
        tech_latest = [
                {
                    "title": "Monzo's former CEO shares 3 tips for getting the most out of vibe coding",
                    "description": "Tom Blomfield, former CEO of Monzo and current Y Combinator partner, shares strategies for maximizing 'vibe coding,' a new approach to programming that uses AI to generate code via text instructions.",
                    "url": "https://www.businessinsider.com/monzo-tom-blomfield-vibe-coding-tips-ai-tools-2025-4",
                    "image": "https://i.insider.com/5d10cee30a28493f9f343be3?width=1300&format=jpeg&auto=webp",
                    "source": "Business Insider",
                    "date": "2025-04-28"
                },
                {
                    "title": "Nvidia Thinks It Has a Better Way of Building AI Agents",
                    "description": "Nvidia has launched a new software platform called NeMo microservices to enable businesses to build their own autonomous AI agents, emphasizing the use of open-weight AI models for greater flexibility.",
                    "url": "https://www.wsj.com/articles/nvidia-thinks-it-has-a-better-way-of-building-ai-agents-b289a574",
                    "image": "https://images.wsj.net/im-87285111?width=700&size=1.518&pixel_ratio=1.5",
                    "source": "The Wall Street Journal",
                    "date": "2025-04-23"
                },
                {
                    "title": "Introducing Gemini 2.0: our new AI model for the agentic era",
                    "description": "Google DeepMind introduces Gemini 2.0, a new AI model designed for the 'agentic era,' featuring native image and audio output and tool use.",
                    "url": "https://blog.google/technology/google-deepmind/google-gemini-ai-update-december-2024/",
                    "image": "https://storage.googleapis.com/gweb-uniblog-publish-prod/images/blog_gemini_keyword_header.width-1600.format-webp.webp",
                    "source": "Google Blog",
                    "date": "2024-12-06"
                },
                {
                    "title": "Cisco Launches Foundation AI and Introduces Open-Source Security AI Model",
                    "description": "Cisco has unveiled Foundation AI, an open-source initiative focused on cybersecurity, featuring the 'Security AI Reasoning Model,' an 8-billion-parameter language model trained exclusively on cybersecurity data.",
                    "url": "https://www.techzine.eu/news/security/130906/cisco-launches-foundation-ai-and-introduces-open-source-security-ai-model/",
                    "image": "https://www.techzine.eu/wp-content/uploads/2025/04/shutterstock_2422220481.jpg",
                    "source": "Techzine Europe",
                    "date": "2025-04-28"
                            },
                {
                    "title": "Microsoft Launches Recall and Click to Do Features in Windows 11",
                    "description": "Microsoft has officially released the Recall feature for Copilot+ PCs, capturing and storing screenshots of user activity to enable comprehensive search functionality. Additionally, 'Click to Do' allows users to perform contextual actions through keyboard shortcuts or touchscreen gestures.",
                    "url": "https://www.tomshardware.com/software/windows/microsoft-launches-recall-to-windows-11-general-availability-click-to-do-and-improved-search-also-coming",
                    "image": "https://cdn.mos.cms.futurecdn.net/UFwtZJ6bYD5RhChCzXSzTJ-970-80.jpg.webp",
                    "source": "Tom's Hardware",
                    "date": "2025-04-26"
                },
                {
                    "title": "Baidu Unveils Ernie 4.5 Turbo and Ernie X1 Turbo AI Models",
                    "description": "At its annual developer conference, Baidu introduced two new AI models: Ernie 4.5 Turbo, matching top industry standards in coding and language comprehension, and the reasoning model Ernie X1 Turbo.",
                    "url": "https://www.reuters.com/world/china/chinas-baidu-says-its-kunlun-chip-cluster-can-train-deepseek-like-models-2025-04-25/",
                    "image": "https://www.reuters.com/resizer/v2/Y23KWZ3XPJMGRMZLOORCDOGQTU.jpg?auth=bbe5096e9600d38d0d18c3f7389a732da30d621db97e47c7d773f498e4cd9883&width=720&quality=80",
                    "source": "Reuters",
                    "date": "2025-04-25"
                },
                {
                    "title": "OpenAI Expands 'Operator' AI Agent to Multiple Countries",
                    "description": "OpenAI has expanded access to its AI agent 'Operator,' beyond the US, making it available in multiple countries including India. The tool can autonomously browse the internet and perform tasks online, making it more of a digital assistant than just a chatbot.",
                    "url": "https://thetechportal.com/2025/02/22/openai-expands-its-operator-ai-agent-in-several-countries-including-india/",
                    "image": "https://thetechportal.com/wp-content/uploads/2023/01/openai-the-tech-portal.png.webp",
                    "source": "The Tech Portal",
                    "date": "2025-02-22"
                },
                {
                    "title": "Adobe Launches Firefly Image Model 4 at Adobe Max London 2025",
                    "description": "At Adobe Max London 2025, Adobe unveiled Firefly Image Model 4, offering hyper-realistic image generation, along with Firefly Boards, a collaborative AI moodboarding tool now in public beta.",
                    "url": "https://www.techradar.com/news/live/adobe-max-london-2025-live",
                    "image": "https://cdn.mos.cms.futurecdn.net/MC5fKSSCWvCPp9nBvHbGeE-970-80.jpg.webp",
                    "source": "TechRadar",
                    "date": "2025-04-24"
                }
            ]


        tech_news = [
            {
                "title": "IBM to Invest $150 Billion in U.S. to Advance Quantum Computing",
                "description": "IBM has announced a $150 billion investment in the United States over the next five years, aiming to support domestic manufacturing and advance quantum computing technology.",
                "url": "https://www.reuters.com/business/ibm-invest-150-billion-us-over-next-five-years-2025-04-28/",
                "image": "https://www.reuters.com/resizer/v2/OZR32ML2FVO3JMNEOZGUX4CZA4.jpg?auth=d5ae041a0ca0c7c7cf8fcf288f7f19bf4ee6e3053023607722b08dbb3101c9b3&width=720&quality=80",
                "source": "Reuters",
                "date": "2025-04-28"
            },
            {
                "title": "Huawei Develops New AI Chip, Seeking to Match Nvidia",
                "description": "Huawei Technologies is preparing to test its most advanced AI chip yet, the Ascend 910D, aiming to compete with U.S. tech giant Nvidia’s high-end AI processors.",
                "url": "https://www.wsj.com/tech/chinas-huawei-develops-new-ai-chip-seeking-to-match-nvidia-8166f606",
                "image": "https://imgs.search.brave.com/jJUyov4HlZSMPWkDRHCoYuZtu8ZuWpswHC7YObVj1AE/rs:fit:860:0:0:0/g:ce/aHR0cHM6Ly9tZWRp/YS5nZXR0eWltYWdl/cy5jb20vaWQvMTM3/MDQ3OTQxNy9waG90/by9hcnRpZmljaWFs/LWludGVsbGlnZW5j/ZS1jaXJjdWl0LWJv/YXJkLTUuanBnP3M9/NjEyeDYxMiZ3PTAm/az0yMCZjPURNdDBh/YUFiOTFRVXZhSXND/VzNOVk1Qa3FtQjVm/TDhaVzRDR1RSd2F3/UzA9",
                "source": "The Wall Street Journal",
                "date": "2025-04-28"
            },
            {
                "title": "Palo Alto Networks Acquires Startup Protect AI as RSA Conference Kicks Off",
                "description": "Palo Alto Networks has acquired the artificial intelligence startup Protect AI, coinciding with the start of the RSA cybersecurity conference in San Francisco.",
                "url": "https://www.investors.com/news/technology/cybersecurity-stocks-palo-alto-stock-rsa-conference/",
                "image": "https://www.investors.com/wp-content/uploads/2017/03/SILO-AUTO-95Comp-031417-shutter.jpg",
                "source": "Investor's Business Daily",
                "date": "2025-04-28"
            },
            {
                "title": "Cerebras Unveils Six Data Centers to Meet Accelerating Demand for AI Inference at Scale",
                "description": "Cerebras announces the deployment of over 300 CS-3 systems in new data centers to meet the growing demand for AI inference at scale.",
                "url": "https://www.datacenterfrontier.com/hyperscale/article/55273769/cerebras-unveils-six-data-centers-to-meet-accelerating-demand-for-ai-inference-at-scale",
                "image": "https://img.datacenterfrontier.com/files/base/ebm/datacenterfrontier/image/2025/03/67d05bfa189931bf0cf636c8-cs3.png?auto=format,compress&fit=max&q=45&w=950&width=950",
                "source": "Data Center Frontier",
                "date": "2025-03-25"
            }
        ]

        trends = [
            {
                "title": "Top 10 Technology Trends to Watch in 2025",
                "description": "Technology is evolving at an unprecedented pace, reshaping industries and changing how people live and work. By 2025, expect groundbreaking advancements that will drive innovation, enhance efficiency, and create new opportunities.",
                "url": "https://www.analyticsinsight.net/tech-news/top-10-technology-trends-to-watch-in-2025",
                "image": "https://media.assettype.com/analyticsinsight%2F2024-11-20%2Fznimr7df%2FTop-10-Technology-Trends-to-Watch-in-2025.jpg?w=1024&auto=format%2Ccompress&fit=max",
                "date": "2024-11-20"
            },
            {
                "title": "Emerging Technology Trends You Need to Know in 2025",
                "description": "From next-gen 5G connectivity to quantum computing, discover the emerging technology trends that will shape 2025.",
                "url": "https://www.office1.com/blog/emerging-technology-trends-you-need-to-know",
                "image": "https://imgs.search.brave.com/gz0Cj3El3NhWHIVH5RKWqPVc0S2laMvssJlmsTlYnaQ/rs:fit:860:0:0:0/g:ce/aHR0cHM6Ly9tZWRp/YS5pc3RvY2twaG90/by5jb20vaWQvMTE2/MDgxMzI1Mi9waG90/by9jbG91ZC5qcGc_/cz02MTJ4NjEyJnc9/MCZrPTIwJmM9ZV95/Wkh5UUtqb2d2bmVF/Y1Z4dGpCTU9aeXJM/NmZsaUNqeVlUZ1JI/cF81WT0",
                "date": "2025-01-15"
            },
            {
                "title": "Explore Gartner's Top 10 Strategic Technology Trends for 2025",
                "description": "Gartner identifies key strategic technology trends for 2025, including Agentic AI, Post-quantum Cryptography, and Spatial Computing.",
                "url": "https://www.gartner.com/en/articles/top-technology-trends-2025",
                "image": "https://emt.gartnerweb.com/ngw/globalassets/en/articles/images/2025-top-10-strategic-technology-trends.png",
                "date": "2025-01-15"
            },
            {
                "title": "Top 10 Technology Trends For 2025",
                "description": "Nuclear energy is set to dominate in 2025, with growing interest in clean, reliable power to meet rising energy demands from AI and high-energy computing.",
                "url": "https://www.forbes.com/councils/forbestechcouncil/2025/02/03/top-10-technology-trends-for-2025/",
                "image": "https://imageio.forbes.com/specials-images/imageserve/66e8ad4b29ea61509edd8b63//960x0.jpg?format=jpg&width=1440",
                "date": "2025-02-03"
            }
        ]

        reads = [
            {
                "title": "Comprehensive Guide to Llama 3: Meta's Open-Source Giant",
                "description": "Learn everything about the Llama 3 model family, capabilities, and how to fine-tune them.",
                "url": "https://ai.meta.com/blog/meta-llama-3/",
                "author": "Meta",
                "date": "2025-04-01"
            },
            {
                "title": "Transformer Models: The Definitive Research Overview",
                "description": "A deep dive into the architectures and innovations post-Transformer era.",
                "url": "https://arxiv.org/abs/2309.00729",
                "author": "arXiv.org",
                "date": "2025-03-15"
            },
            {
                "title": "Fine-tuning Open-Source LLMs for Real-World Applications",
                "description": "Step-by-step tutorial to fine-tune open-source large language models for enterprise use cases.",
                "url": "https://towardsdatascience.com/fine-tuning-llms/",
                "author": "Towards Data Science",
                "date": "2025-02-28"
            },
            {
                "title": "7 Must Read Tech Books for Experienced Developers and Leads in 2025",
                "description": "A curated list of essential tech books for experienced developers and leads to enhance their knowledge and skills.",
                "url": "https://dev.to/somadevtoo/7-must-read-tech-books-for-experienced-developers-and-leads-in-2025-2j0n",
                "author": "Dev.to",
                "date": "2025-03-10"
            },
            {
                "title": "A Critical Tech Reading List for Spring 2025",
                "description": "An insightful selection of tech books and articles to read in Spring 2025, covering various aspects of technology and society.",
                "url": "https://www.disconnect.blog/p/a-critical-tech-reading-list-for-09f",
                "author": "Disconnect",
                "date": "2025-04-14"
            }
        ]

        # Fill the mock data
        for i, interest in enumerate(main_interests):
            date = (today - timedelta(days=random.randint(0, 5))).strftime("%Y-%m-%d")
            
            # New Technologies
            tech_ar = tech_latest[i % len(tech_news)]
            mock_data["New Technologies"].append({
                "title": tech_ar["title"],
                "description": tech_ar["description"],
                "url": tech_ar["url"],
                "date": date,
                "image": tech_ar["image"],
                "source": tech_ar["source"],
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
