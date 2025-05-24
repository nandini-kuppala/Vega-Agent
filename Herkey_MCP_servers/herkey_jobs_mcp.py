#!/usr/bin/env python3
"""
MCP Server for Herkey.com Job Data
Provides real-time job scraping capabilities via MCP protocol

User: "Find me remote React developer jobs in Bangalore"

LLM uses MCP tools:
1. get_latest_jobs(location_filter="Bangalore", work_type_filter="remote")
2. search_jobs(query="React", search_type="skills")

Result: Filtered, relevant job listings

"""
import asyncio
import json
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import hashlib

# MCP imports
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

# Import your existing scraper
from herkey_scraper import HerkeyJobScraper, recommend_jobs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("herkey-mcp-server")

class HerkeyMCPServer:
    def __init__(self):
        self.server = Server("herkey-job-server")
        self.scraper = HerkeyJobScraper(headless=True)
        self.cache = {}
        self.cache_duration = timedelta(minutes=30)  # Cache data for 30 minutes
        
        # Register tools and resources
        self._register_tools()
        self._register_resources()
    
    def _register_tools(self):
        """Register all available tools"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            return [
                Tool(
                    name="get_latest_jobs",
                    description="Fetch the latest job postings from Herkey.com with optional filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "max_scroll": {
                                "type": "integer",
                                "description": "Number of scroll actions to load more jobs (1-10)",
                                "default": 3,
                                "minimum": 1,
                                "maximum": 10
                            },
                            "location_filter": {
                                "type": "string",
                                "description": "Filter jobs by location (optional)"
                            },
                            "work_type_filter": {
                                "type": "string",
                                "description": "Filter by work type: remote, hybrid, in-office (optional)"
                            },
                            "use_cache": {
                                "type": "boolean",
                                "description": "Whether to use cached data if available",
                                "default": True
                            }
                        }
                    }
                ),
                Tool(
                    name="recommend_jobs_for_candidate",
                    description="Get personalized job recommendations based on candidate profile",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "candidate_profile": {
                                "type": "object",
                                "description": "Candidate profile with skills, experience, preferences",
                                "properties": {
                                    "name": {"type": "string"},
                                    "years_of_experience": {"type": "integer"},
                                    "skills": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "preferred_work_mode": {
                                        "type": "string",
                                        "enum": ["remote", "hybrid", "in-office", "any"]
                                    },
                                    "preferred_locations": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                },
                                "required": ["skills", "years_of_experience"]
                            },
                            "num_recommendations": {
                                "type": "integer",
                                "description": "Number of job recommendations to return",
                                "default": 5,
                                "minimum": 1,
                                "maximum": 20
                            },
                            "force_fresh_data": {
                                "type": "boolean",
                                "description": "Force fetching fresh data instead of using cache",
                                "default": False
                            }
                        },
                        "required": ["candidate_profile"]
                    }
                ),
                Tool(
                    name="search_jobs",
                    description="Search jobs by keywords, skills, or company names",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (keywords, skills, company names)"
                            },
                            "search_type": {
                                "type": "string",
                                "enum": ["title", "company", "skills", "all"],
                                "description": "Type of search to perform",
                                "default": "all"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_job_market_insights",
                    description="Get insights about the job market from current listings",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "insight_type": {
                                "type": "string",
                                "enum": ["skills_demand", "location_trends", "work_type_distribution", "experience_levels"],
                                "description": "Type of market insight to generate"
                            }
                        },
                        "required": ["insight_type"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            try:
                if name == "get_latest_jobs":
                    return await self._get_latest_jobs(**arguments)
                elif name == "recommend_jobs_for_candidate":
                    return await self._recommend_jobs(**arguments)
                elif name == "search_jobs":
                    return await self._search_jobs(**arguments)
                elif name == "get_job_market_insights":
                    return await self._get_market_insights(**arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    def _register_resources(self):
        """Register available resources"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            return [
                Resource(
                    uri="herkey://jobs/latest",
                    name="Latest Jobs",
                    description="Latest job listings from Herkey.com",
                    mimeType="application/json"
                ),
                Resource(
                    uri="herkey://jobs/cache-status",
                    name="Cache Status",
                    description="Current cache status and statistics",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            if uri == "herkey://jobs/latest":
                jobs = await self._fetch_jobs_with_cache()
                return json.dumps(jobs, indent=2)
            elif uri == "herkey://jobs/cache-status":
                return json.dumps(self._get_cache_status(), indent=2)
            else:
                raise ValueError(f"Unknown resource: {uri}")
    
    async def _get_latest_jobs(self, max_scroll: int = 3, location_filter: Optional[str] = None, 
                             work_type_filter: Optional[str] = None, use_cache: bool = True) -> List[TextContent]:
        """Fetch latest jobs with optional filtering"""
        
        # Get jobs (with caching if enabled)
        if use_cache:
            jobs = await self._fetch_jobs_with_cache(max_scroll)
        else:
            jobs = await self._fetch_jobs_fresh(max_scroll)
        
        # Apply filters
        filtered_jobs = self._apply_filters(jobs, location_filter, work_type_filter)
        
        result = {
            "total_jobs": len(filtered_jobs),
            "filters_applied": {
                "location": location_filter,
                "work_type": work_type_filter
            },
            "jobs": filtered_jobs,
            "timestamp": datetime.now().isoformat(),
            "data_source": "cache" if use_cache and self._is_cache_valid() else "fresh_scrape"
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _recommend_jobs(self, candidate_profile: Dict, num_recommendations: int = 5, 
                            force_fresh_data: bool = False) -> List[TextContent]:
        """Get personalized job recommendations"""
        
        # Get jobs data
        if force_fresh_data:
            jobs = await self._fetch_jobs_fresh()
        else:
            jobs = await self._fetch_jobs_with_cache()
        
        # Process jobs for recommendation engine
        processed_jobs = self.scraper.job_recommendation_data(jobs)
        
        # Get recommendations
        recommendations = recommend_jobs(candidate_profile, processed_jobs, num_recommendations)
        
        result = {
            "candidate": candidate_profile.get("name", "Anonymous"),
            "total_jobs_analyzed": len(processed_jobs),
            "recommendations_count": len(recommendations),
            "recommendations": recommendations,
            "matching_criteria": {
                "skills_weight": 10,
                "experience_weight": 5,
                "work_mode_weight": 3,
                "location_weight": 2
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _search_jobs(self, query: str, search_type: str = "all") -> List[TextContent]:
        """Search jobs by query"""
        
        jobs = await self._fetch_jobs_with_cache()
        query_lower = query.lower()
        
        matching_jobs = []
        for job in jobs:
            match = False
            
            if search_type in ["title", "all"]:
                if query_lower in job.get("title", "").lower():
                    match = True
            
            if search_type in ["company", "all"]:
                if query_lower in job.get("company", "").lower():
                    match = True
            
            if search_type in ["skills", "all"]:
                skills_text = job.get("skills", "").lower()
                if query_lower in skills_text:
                    match = True
            
            if match:
                matching_jobs.append(job)
        
        result = {
            "query": query,
            "search_type": search_type,
            "total_matches": len(matching_jobs),
            "matches": matching_jobs,
            "timestamp": datetime.now().isoformat()
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _get_market_insights(self, insight_type: str) -> List[TextContent]:
        """Generate market insights from job data"""
        
        jobs = await self._fetch_jobs_with_cache()
        
        if insight_type == "skills_demand":
            insights = self._analyze_skills_demand(jobs)
        elif insight_type == "location_trends":
            insights = self._analyze_location_trends(jobs)
        elif insight_type == "work_type_distribution":
            insights = self._analyze_work_type_distribution(jobs)
        elif insight_type == "experience_levels":
            insights = self._analyze_experience_levels(jobs)
        else:
            insights = {"error": f"Unknown insight type: {insight_type}"}
        
        result = {
            "insight_type": insight_type,
            "total_jobs_analyzed": len(jobs),
            "insights": insights,
            "timestamp": datetime.now().isoformat()
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _fetch_jobs_with_cache(self, max_scroll: int = 3) -> List[Dict]:
        """Fetch jobs with caching mechanism"""
        
        cache_key = f"jobs_{max_scroll}"
        
        # Check if cache is valid
        if cache_key in self.cache and self._is_cache_valid(cache_key):
            logger.info("Using cached job data")
            return self.cache[cache_key]["data"]
        
        # Fetch fresh data
        return await self._fetch_jobs_fresh(max_scroll)
    
    async def _fetch_jobs_fresh(self, max_scroll: int = 3) -> List[Dict]:
        """Fetch fresh job data from Herkey"""
        
        logger.info(f"Fetching fresh job data with max_scroll={max_scroll}")
        
        # Run scraping in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        jobs = await loop.run_in_executor(
            None, 
            lambda: self.scraper.scrape_jobs(max_scroll=max_scroll)
        )
        
        # Cache the results
        cache_key = f"jobs_{max_scroll}"
        self.cache[cache_key] = {
            "data": jobs,
            "timestamp": datetime.now()
        }
        
        logger.info(f"Cached {len(jobs)} jobs")
        return jobs
    
    def _is_cache_valid(self, cache_key: str = None) -> bool:
        """Check if cache is still valid"""
        if not cache_key:
            return any(
                datetime.now() - entry["timestamp"] < self.cache_duration
                for entry in self.cache.values()
            )
        
        if cache_key not in self.cache:
            return False
        
        return datetime.now() - self.cache[cache_key]["timestamp"] < self.cache_duration
    
    def _apply_filters(self, jobs: List[Dict], location_filter: Optional[str], 
                      work_type_filter: Optional[str]) -> List[Dict]:
        """Apply filters to job list"""
        
        filtered_jobs = jobs
        
        if location_filter:
            filtered_jobs = [
                job for job in filtered_jobs
                if location_filter.lower() in job.get("location", "").lower()
            ]
        
        if work_type_filter:
            filtered_jobs = [
                job for job in filtered_jobs
                if work_type_filter.lower() in job.get("work_type", "").lower()
            ]
        
        return filtered_jobs
    
    def _analyze_skills_demand(self, jobs: List[Dict]) -> Dict:
        """Analyze skills demand from job listings"""
        skills_count = {}
        
        for job in jobs:
            skills_text = job.get("skills", "")
            # Simple skill extraction - you might want to improve this
            skills = [skill.strip() for skill in skills_text.replace("•", ",").split(",") if skill.strip()]
            
            for skill in skills:
                if skill and not skill.startswith("+"):  # Ignore "+n more" type entries
                    skills_count[skill] = skills_count.get(skill, 0) + 1
        
        # Get top 20 skills
        top_skills = sorted(skills_count.items(), key=lambda x: x[1], reverse=True)[:20]
        
        return {
            "top_skills": [{"skill": skill, "job_count": count} for skill, count in top_skills],
            "total_unique_skills": len(skills_count)
        }
    
    def _analyze_location_trends(self, jobs: List[Dict]) -> Dict:
        """Analyze location trends"""
        location_count = {}
        
        for job in jobs:
            location = job.get("location", "").strip()
            if location:
                location_count[location] = location_count.get(location, 0) + 1
        
        top_locations = sorted(location_count.items(), key=lambda x: x[1], reverse=True)[:15]
        
        return {
            "top_locations": [{"location": loc, "job_count": count} for loc, count in top_locations],
            "total_locations": len(location_count)
        }
    
    def _analyze_work_type_distribution(self, jobs: List[Dict]) -> Dict:
        """Analyze work type distribution"""
        work_type_count = {}
        
        for job in jobs:
            work_type = job.get("work_type", "").strip()
            if work_type:
                work_type_count[work_type] = work_type_count.get(work_type, 0) + 1
        
        total_jobs = len(jobs)
        distribution = [
            {
                "work_type": wt,
                "job_count": count,
                "percentage": round((count / total_jobs) * 100, 1)
            }
            for wt, count in work_type_count.items()
        ]
        
        return {
            "distribution": sorted(distribution, key=lambda x: x["job_count"], reverse=True),
            "total_jobs": total_jobs
        }
    
    def _analyze_experience_levels(self, jobs: List[Dict]) -> Dict:
        """Analyze experience level requirements"""
        experience_count = {}
        
        for job in jobs:
            experience = job.get("experience", "").strip()
            if experience:
                experience_count[experience] = experience_count.get(experience, 0) + 1
        
        return {
            "experience_levels": [
                {"level": exp, "job_count": count}
                for exp, count in sorted(experience_count.items(), key=lambda x: x[1], reverse=True)
            ],
            "total_levels": len(experience_count)
        }
    
    def _get_cache_status(self) -> Dict:
        """Get current cache status"""
        status = {
            "cache_entries": len(self.cache),
            "cache_duration_minutes": self.cache_duration.total_seconds() / 60,
            "entries": []
        }
        
        for key, entry in self.cache.items():
            age = datetime.now() - entry["timestamp"]
            status["entries"].append({
                "key": key,
                "job_count": len(entry["data"]),
                "age_minutes": age.total_seconds() / 60,
                "is_valid": age < self.cache_duration
            })
        
        return status
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="herkey-job-server",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification=True,
                        tools=True,
                        resources=True,
                    ),
                ),
            )

def main():
    """Main entry point"""
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stderr)]
    )
    
    # Create and run server
    server = HerkeyMCPServer()
    asyncio.run(server.run())

if __name__ == "__main__":
    main()