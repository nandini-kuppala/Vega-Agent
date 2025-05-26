import os
import json
import google.generativeai as genai
from tavily import TavilyClient
import streamlit as st
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TavilyJobAgent:
    def __init__(self):
        """Initialize the Tavily Job Agent with API keys."""
        try:
            # Initialize Gemini
            self.gemini_api_key = st.secrets.get("GEMINI_API_KEY")
            if self.gemini_api_key:
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-pro')
            else:
                logger.warning("GEMINI_API_KEY not found in secrets")
                self.gemini_model = None
            
            # Initialize Tavily
            self.tavily_api_key = st.secrets["TAVILY_API_KEY"]
            self.tavily_client = TavilyClient(self.tavily_api_key)
            
        except Exception as e:
            logger.error(f"Error initializing TavilyJobAgent: {e}")
            self.gemini_model = None
            self.tavily_client = None

    def generate_personalized_query(self, profile: Dict) -> str:
        """Generate a personalized job search query using Gemini AI."""
        if not self.gemini_model:
            # Fallback query generation without AI
            return self._generate_fallback_query(profile)
        
        try:
            # Create a detailed prompt for Gemini
            prompt = f"""
            Based on the following user profile, generate a highly specific and effective job search query for Tavily that will find the most relevant job opportunities. The query should be concise but comprehensive enough to capture the user's requirements.

            User Profile:
            - Skills: {', '.join(profile.get('skills', []))}
            - Experience: {profile.get('experience_years', 0)} years
            - Last Job: {profile.get('last_job', {}).get('title', 'N/A')} at {profile.get('last_job', {}).get('company', 'N/A')}
            - Education: {profile.get('education', 'N/A')}
            - Job Preferences: {profile.get('job_preferences', {}).get('type', 'N/A')}
            - Preferred Roles: {', '.join(profile.get('job_preferences', {}).get('roles', []))}
            - Location: {profile.get('location', {}).get('city', 'N/A')}
            - Work Mode: {profile.get('location', {}).get('work_mode', 'N/A')}
            - Relocation: {profile.get('location', {}).get('relocation', False)}
            - Short-term Goal: {profile.get('job_preferences', {}).get('short_term_goal', '')}
            - Long-term Goal: {profile.get('job_preferences', {}).get('long_term_goal', '')}

            Generate a job search query that includes:
            1. Key skills and technologies
            2. Job titles/roles
            3. Experience level
            4. Location preferences
            5. Work arrangement preferences

            Return ONLY the search query, nothing else. Make it optimized for job search engines.
            """

            response = self.gemini_model.generate_content(prompt)
            query = response.text.strip()
            
            # Clean up the query
            query = query.replace('"', '').replace("'", "")
            
            logger.info(f"Generated personalized query: {query}")
            return query
            
        except Exception as e:
            logger.error(f"Error generating personalized query with Gemini: {e}")
            return self._generate_fallback_query(profile)

    def _generate_fallback_query(self, profile: Dict) -> str:
        """Generate a fallback query without AI when Gemini is not available."""
        skills = profile.get('skills', [])
        roles = profile.get('job_preferences', {}).get('roles', [])
        experience = profile.get('experience_years', 0)
        location = profile.get('location', {}).get('city', '')
        work_mode = profile.get('location', {}).get('work_mode', '')
        
        # Build query components
        query_parts = []
        
        # Add primary skills
        if skills:
            primary_skills = skills[:3]  # Take top 3 skills
            query_parts.append(' '.join(primary_skills))
        
        # Add job roles
        if roles:
            query_parts.extend(roles)
        
        # Add experience level
        if experience == 0:
            query_parts.append("entry level junior")
        elif experience <= 2:
            query_parts.append("junior")
        elif experience <= 5:
            query_parts.append("mid level")
        else:
            query_parts.append("senior")
        
        # Add location if specific
        if location and location.lower() != 'flexible':
            query_parts.append(location)
        
        # Add work mode
        if work_mode and work_mode.lower() == 'remote':
            query_parts.append("remote")
        
        query_parts.append("jobs")
        
        return ' '.join(query_parts)

    def search_jobs(self, query: str, max_results: int = 8) -> Optional[Dict]:
        """Search for jobs using Tavily with the generated query."""
        if not self.tavily_client:
            logger.error("Tavily client not initialized")
            return None
        
        try:
            response = self.tavily_client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_domains=["linkedin.com", "indeed.com", "glassdoor.com", "naukri.com", "monster.com"]
            )
            
            logger.info(f"Tavily search completed. Found {len(response.get('results', []))} results")
            return response
            
        except Exception as e:
            logger.error(f"Error in Tavily job search: {e}")
            return None

    def format_job_results(self, tavily_response: Dict, profile: Dict) -> List[Dict]:
        """Format Tavily search results into structured job recommendations."""
        if not tavily_response or not tavily_response.get('results'):
            return []
        
        results = tavily_response['results']
        formatted_jobs = []
        user_skills = set(skill.lower() for skill in profile.get('skills', []))
        
        for i, result in enumerate(results[:8], 1):
            title = result.get('title', 'Job Opportunity')
            url = result.get('url', '#')
            content = result.get('content', '')
            
            # Extract job information from title and content
            job_info = self._extract_job_info(title, content, user_skills)
            
            formatted_job = {
                'id': i,
                'job_title': job_info.get('title', title),
                'company': job_info.get('company', 'Company'),
                'location': job_info.get('location', 'Location not specified'),
                'experience_required': job_info.get('experience', 'Not specified'),
                'match_percentage': job_info.get('match_percentage', 75.0),
                'skills_match': job_info.get('matching_skills', []),
                'job_link': url,
                'description': content[:200] + "..." if len(content) > 200 else content
            }
            
            formatted_jobs.append(formatted_job)
        
        return formatted_jobs

    def _extract_job_info(self, title: str, content: str, user_skills: set) -> Dict:
        """Extract structured information from job title and content."""
        info = {}
        
        # Extract job title (clean up)
        title_parts = title.split(' - ')
        if len(title_parts) >= 2:
            info['title'] = title_parts[0].strip()
            remaining = ' - '.join(title_parts[1:])
            
            # Try to extract company from remaining parts
            company_indicators = ['at', 'with', '|']
            for indicator in company_indicators:
                if indicator in remaining.lower():
                    parts = remaining.split(indicator)
                    if len(parts) > 1:
                        info['company'] = parts[-1].strip()
                        break
        else:
            info['title'] = title.strip()
        
        # Extract location from content
        location_keywords = ['location:', 'based in', 'office in', 'remote', 'hybrid']
        content_lower = content.lower()
        for keyword in location_keywords:
            if keyword in content_lower:
                # Simple extraction - could be improved
                if 'remote' in content_lower:
                    info['location'] = 'Remote'
                    break
                elif 'hybrid' in content_lower:
                    info['location'] = 'Hybrid'
                    break
        
        # Calculate skill match
        content_skills = set()
        for skill in user_skills:
            if skill in content_lower:
                content_skills.add(skill.title())
        
        info['matching_skills'] = list(content_skills)
        
        # Calculate match percentage based on skill overlap
        if user_skills and content_skills:
            match_ratio = len(content_skills) / len(user_skills)
            info['match_percentage'] = min(95.0, max(60.0, match_ratio * 100))
        else:
            info['match_percentage'] = 70.0
        
        # Extract experience level
        experience_patterns = ['fresher', 'entry level', '0-1', '1-2', '2-3', '3-5', '5+', 'senior']
        for pattern in experience_patterns:
            if pattern in content_lower:
                info['experience'] = pattern.replace('-', ' to ') + ' years'
                break
        
        return info

    def get_job_recommendations(self, profile: Dict) -> Dict:
        """Main method to get job recommendations for a user profile."""
        try:
            # Step 1: Generate personalized query
            query = self.generate_personalized_query(profile)
            logger.info(f"Using query: {query}")
            
            # Step 2: Search jobs using Tavily
            tavily_response = self.search_jobs(query)
            
            if not tavily_response:
                return {
                    "status": "error",
                    "message": "Unable to fetch job recommendations at the moment",
                    "recommendations": []
                }
            
            # Step 3: Format results
            formatted_jobs = self.format_job_results(tavily_response, profile)
            
            return {
                "status": "success",
                "query_used": query,
                "total_results": len(formatted_jobs),
                "recommendations": formatted_jobs
            }
            
        except Exception as e:
            logger.error(f"Error in get_job_recommendations: {e}")
            return {
                "status": "error",
                "message": f"Error getting recommendations: {str(e)}",
                "recommendations": []
            }

# Utility functions for backward compatibility
def get_tavily_search_results(query: str, search_type: str = "general") -> Optional[Dict]:
    """Utility function for general Tavily searches."""
    agent = TavilyJobAgent()
    if search_type == "jobs":
        return agent.search_jobs(query)
    else:
        try:
            response = agent.tavily_client.search(
                query=query,
                search_depth="basic",
                max_results=6
            )
            return response
        except Exception as e:
            logger.error(f"Error in general Tavily search: {e}")
            return None

def format_tavily_results(tavily_response: Dict, query_type: str = "general") -> List[Dict]:
    """Utility function to format general Tavily results."""
    if not tavily_response or not tavily_response.get('results'):
        return []
    
    results = tavily_response['results']
    formatted_results = []
    
    for result in results:
        title = result.get('title', 'No title')
        url = result.get('url', '#')
        content = result.get('content', '')[:200] + "..." if result.get('content') else ''
        
        formatted_results.append({
            'title': title,
            'url': url,
            'content': content
        })
    
    return formatted_results