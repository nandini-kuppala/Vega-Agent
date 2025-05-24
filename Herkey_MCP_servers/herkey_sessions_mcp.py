#!/usr/bin/env python3
"""
MCP Server for Herkey.com Events Data
Provides real-time event scraping capabilities via MCP protocol
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import hashlib
from collections import Counter

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

# Import your existing event scraper
from herkey_event_scraper import HerkeyEventScraper, recommend_sessions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("herkey-sessions-mcp-server")

class HerkeyEventsMCPServer:
    def __init__(self):
        self.server = Server("herkey-sessions-server")
        self.scraper = HerkeyEventScraper()
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
                    name="get_latest_sessions",
                    description="Fetch the latest sessions from Herkey.com with optional filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "event_mode_filter": {
                                "type": "string",
                                "enum": ["online", "offline", "all"],
                                "description": "Filter sessions by mode (online/offline)",
                                "default": "all"
                            },
                            "location_filter": {
                                "type": "string",
                                "description": "Filter sessions by location (for offline sessions)"
                            },
                            "category_filter": {
                                "type": "string",
                                "description": "Filter sessions by category/topic"
                            },
                            "price_filter": {
                                "type": "string",
                                "enum": ["free", "paid", "all"],
                                "description": "Filter sessions by price (free/paid)",
                                "default": "all"
                            },
                            "upcoming_only": {
                                "type": "boolean",
                                "description": "Only return upcoming sessions",
                                "default": True
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
                    name="recommend_sessions_for_candidate",
                    description="Get personalized event recommendations based on candidate profile",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "candidate_profile": {
                                "type": "object",
                                "description": "Candidate profile with interests, preferences, career stage",
                                "properties": {
                                    "name": {"type": "string"},
                                    "interests": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Areas of interest (Technology, Career Development, etc.)"
                                    },
                                    "preferred_event_mode": {
                                        "type": "string",
                                        "enum": ["online", "offline", "hybrid", "any"],
                                        "description": "Preferred event mode"
                                    },
                                    "preferred_locations": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Preferred cities/locations"
                                    },
                                    "career_stage": {
                                        "type": "string",
                                        "enum": ["entry-level", "mid-level", "senior-level", "executive"],
                                        "description": "Current career stage"
                                    },
                                    "availability": {
                                        "type": "object",
                                        "properties": {
                                            "weekdays": {"type": "boolean"},
                                            "weekends": {"type": "boolean"},
                                            "evenings": {"type": "boolean"}
                                        }
                                    }
                                },
                                "required": ["interests"]
                            },
                            "num_recommendations": {
                                "type": "integer",
                                "description": "Number of event recommendations to return",
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
                    name="search_sessions",
                    description="Search sessions by keywords, topics, or organizers",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (keywords, topics, organizer names)"
                            },
                            "search_fields": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["title", "categories", "location", "all"]
                                },
                                "description": "Fields to search in",
                                "default": ["all"]
                            },
                            "date_range": {
                                "type": "object",
                                "properties": {
                                    "start_date": {"type": "string", "format": "date"},
                                    "end_date": {"type": "string", "format": "date"}
                                },
                                "description": "Filter sessions within date range"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_event_market_insights",
                    description="Get insights about the sessions market and trends",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "insight_type": {
                                "type": "string",
                                "enum": [
                                    "popular_categories", 
                                    "location_trends", 
                                    "mode_distribution", 
                                    "pricing_analysis",
                                    "featured_sessions_analysis",
                                    "time_patterns"
                                ],
                                "description": "Type of market insight to generate"
                            },
                            "time_period": {
                                "type": "string",
                                "enum": ["all", "upcoming", "this_month", "next_month"],
                                "description": "Time period for analysis",
                                "default": "upcoming"
                            }
                        },
                        "required": ["insight_type"]
                    }
                ),
                Tool(
                    name="get_event_calendar",
                    description="Get sessions organized by calendar format for specific time periods",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "calendar_view": {
                                "type": "string",
                                "enum": ["week", "month", "quarter"],
                                "description": "Calendar view period",
                                "default": "month"
                            },
                            "start_date": {
                                "type": "string",
                                "format": "date",
                                "description": "Start date for calendar view (YYYY-MM-DD)"
                            },
                            "filters": {
                                "type": "object",
                                "properties": {
                                    "categories": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "mode": {"type": "string", "enum": ["online", "offline", "all"]},
                                    "price": {"type": "string", "enum": ["free", "paid", "all"]}
                                }
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            try:
                if name == "get_latest_sessions":
                    return await self._get_latest_sessions(**arguments)
                elif name == "recommend_sessions_for_candidate":
                    return await self._recommend_sessions(**arguments)
                elif name == "search_sessions":
                    return await self._search_sessions(**arguments)
                elif name == "get_event_market_insights":
                    return await self._get_event_insights(**arguments)
                elif name == "get_event_calendar":
                    return await self._get_event_calendar(**arguments)
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
                    uri="herkey://sessions/latest",
                    name="Latest Events",
                    description="Latest event listings from Herkey.com",
                    mimeType="application/json"
                ),
                Resource(
                    uri="herkey://sessions/upcoming",
                    name="Upcoming Events",
                    description="Upcoming sessions only",
                    mimeType="application/json"
                ),
                Resource(
                    uri="herkey://sessions/cache-status",
                    name="Cache Status",
                    description="Current cache status and statistics",
                    mimeType="application/json"
                ),
                Resource(
                    uri="herkey://sessions/categories",
                    name="Event Categories",
                    description="Available event categories and their counts",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            if uri == "herkey://sessions/latest":
                sessions = await self._fetch_sessions_with_cache()
                return json.dumps(sessions, indent=2, default=str)
            elif uri == "herkey://sessions/upcoming":
                sessions = await self._fetch_sessions_with_cache()
                upcoming_sessions = [e for e in sessions if e.get("is_upcoming", True)]
                return json.dumps(upcoming_sessions, indent=2, default=str)
            elif uri == "herkey://sessions/cache-status":
                return json.dumps(self._get_cache_status(), indent=2)
            elif uri == "herkey://sessions/categories":
                sessions = await self._fetch_sessions_with_cache()
                categories = self._extract_categories(sessions)
                return json.dumps(categories, indent=2)
            else:
                raise ValueError(f"Unknown resource: {uri}")
    
    async def _get_latest_sessions(self, event_mode_filter: str = "all", location_filter: Optional[str] = None,
                               category_filter: Optional[str] = None, price_filter: str = "all",
                               upcoming_only: bool = True, use_cache: bool = True) -> List[TextContent]:
        """Fetch latest sessions with optional filtering"""
        
        # Get sessions (with caching if enabled)
        if use_cache:
            sessions = await self._fetch_sessions_with_cache()
        else:
            sessions = await self._fetch_sessions_fresh()
        
        # Process sessions for filtering
        processed_sessions = self.scraper.process_sessions_for_recommendation(sessions)
        
        # Apply filters
        filtered_sessions = self._apply_event_filters(
            processed_sessions, event_mode_filter, location_filter, 
            category_filter, price_filter, upcoming_only
        )
        
        result = {
            "total_sessions": len(filtered_sessions),
            "filters_applied": {
                "event_mode": event_mode_filter,
                "location": location_filter,
                "category": category_filter,
                "price": price_filter,
                "upcoming_only": upcoming_only
            },
            "sessions": filtered_sessions,
            "timestamp": datetime.now().isoformat(),
            "data_source": "cache" if use_cache and self._is_cache_valid() else "fresh_scrape"
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    
    async def _recommend_sessions(self, candidate_profile: Dict, num_recommendations: int = 5,
                              force_fresh_data: bool = False) -> List[TextContent]:
        """Get personalized event recommendations"""
        
        # Get sessions data
        if force_fresh_data:
            sessions = await self._fetch_sessions_fresh()
        else:
            sessions = await self._fetch_sessions_with_cache()
        
        # Process sessions for recommendation engine
        processed_sessions = self.scraper.process_sessions_for_recommendation(sessions)
        
        # Get recommendations
        recommendations = recommend_sessions(candidate_profile, processed_sessions, num_recommendations)
        
        # Add recommendation scores and reasoning
        scored_recommendations = self._add_recommendation_scores(recommendations, candidate_profile)
        
        result = {
            "candidate": candidate_profile.get("name", "Anonymous"),
            "total_sessions_analyzed": len(processed_sessions),
            "recommendations_count": len(recommendations),
            "recommendations": scored_recommendations,
            "matching_criteria": {
                "interests_weight": 10,
                "event_mode_weight": 5,
                "location_weight": 5,
                "free_sessions_bonus": 2,
                "featured_sessions_bonus": 3,
                "career_stage_weight": 4
            },
            "candidate_profile": candidate_profile,
            "timestamp": datetime.now().isoformat()
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    
    async def _search_sessions(self, query: str, search_fields: List[str] = ["all"],
                           date_range: Optional[Dict] = None) -> List[TextContent]:
        """Search sessions by query"""
        
        sessions = await self._fetch_sessions_with_cache()
        processed_sessions = self.scraper.process_sessions_for_recommendation(sessions)
        query_lower = query.lower()
        
        matching_sessions = []
        for event in processed_sessions:
            match = False
            match_reasons = []
            
            # Search in title
            if "title" in search_fields or "all" in search_fields:
                if query_lower in event.get("title", "").lower():
                    match = True
                    match_reasons.append("title")
            
            # Search in categories
            if "categories" in search_fields or "all" in search_fields:
                categories = event.get("categories", [])
                if any(query_lower in cat.lower() for cat in categories):
                    match = True
                    match_reasons.append("categories")
            
            # Search in location
            if "location" in search_fields or "all" in search_fields:
                if query_lower in event.get("location", "").lower():
                    match = True
                    match_reasons.append("location")
            
            if match:
                event["match_reasons"] = match_reasons
                
                # Apply date range filter if specified
                if date_range:
                    event_date = event.get("datetime_obj")
                    if event_date:
                        start_date = datetime.strptime(date_range.get("start_date"), "%Y-%m-%d") if date_range.get("start_date") else None
                        end_date = datetime.strptime(date_range.get("end_date"), "%Y-%m-%d") if date_range.get("end_date") else None
                        
                        if start_date and event_date < start_date:
                            continue
                        if end_date and event_date > end_date:
                            continue
                
                matching_sessions.append(event)
        
        result = {
            "query": query,
            "search_fields": search_fields,
            "date_range": date_range,
            "total_matches": len(matching_sessions),
            "matches": matching_sessions,
            "timestamp": datetime.now().isoformat()
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    
    async def _get_event_insights(self, insight_type: str, time_period: str = "upcoming") -> List[TextContent]:
        """Generate event market insights"""
        
        sessions = await self._fetch_sessions_with_cache()
        processed_sessions = self.scraper.process_sessions_for_recommendation(sessions)
        
        # Filter by time period
        if time_period == "upcoming":
            sessions_to_analyze = [e for e in processed_sessions if e.get("is_upcoming", True)]
        elif time_period == "this_month":
            current_month = datetime.now().month
            sessions_to_analyze = [e for e in processed_sessions 
                               if e.get("datetime_obj") and e["datetime_obj"].month == current_month]
        elif time_period == "next_month":
            next_month = (datetime.now().month % 12) + 1
            sessions_to_analyze = [e for e in processed_sessions 
                               if e.get("datetime_obj") and e["datetime_obj"].month == next_month]
        else:  # all
            sessions_to_analyze = processed_sessions
        
        if insight_type == "popular_categories":
            insights = self._analyze_popular_categories(sessions_to_analyze)
        elif insight_type == "location_trends":
            insights = self._analyze_location_trends(sessions_to_analyze)
        elif insight_type == "mode_distribution":
            insights = self._analyze_mode_distribution(sessions_to_analyze)
        elif insight_type == "pricing_analysis":
            insights = self._analyze_pricing(sessions_to_analyze)
        elif insight_type == "featured_sessions_analysis":
            insights = self._analyze_featured_sessions(sessions_to_analyze)
        elif insight_type == "time_patterns":
            insights = self._analyze_time_patterns(sessions_to_analyze)
        else:
            insights = {"error": f"Unknown insight type: {insight_type}"}
        
        result = {
            "insight_type": insight_type,
            "time_period": time_period,
            "total_sessions_analyzed": len(sessions_to_analyze),
            "insights": insights,
            "timestamp": datetime.now().isoformat()
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    
    async def _get_event_calendar(self, calendar_view: str = "month", start_date: Optional[str] = None,
                                filters: Optional[Dict] = None) -> List[TextContent]:
        """Get sessions in calendar format"""
        
        sessions = await self._fetch_sessions_with_cache()
        processed_sessions = self.scraper.process_sessions_for_recommendation(sessions)
        
        # Apply filters if specified
        if filters:
            processed_sessions = self._apply_event_filters(
                processed_sessions,
                filters.get("mode", "all"),
                None,  # location filter not applicable here
                None,  # category filter handled separately
                filters.get("price", "all"),
                True   # upcoming only
            )
            
            # Apply category filter
            if filters.get("categories"):
                category_filters = [cat.lower() for cat in filters["categories"]]
                processed_sessions = [
                    event for event in processed_sessions
                    if any(cat in event.get("categories_lower", []) for cat in category_filters)
                ]
        
        # Organize sessions by date
        calendar_data = self._organize_sessions_by_calendar(processed_sessions, calendar_view, start_date)
        
        result = {
            "calendar_view": calendar_view,
            "start_date": start_date,
            "filters": filters,
            "total_sessions": len(processed_sessions),
            "calendar": calendar_data,
            "timestamp": datetime.now().isoformat()
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    
    async def _fetch_sessions_with_cache(self) -> List[Dict]:
        """Fetch sessions with caching mechanism"""
        
        cache_key = "sessions_data"
        
        # Check if cache is valid
        if cache_key in self.cache and self._is_cache_valid(cache_key):
            logger.info("Using cached event data")
            return self.cache[cache_key]["data"]
        
        # Fetch fresh data
        return await self._fetch_sessions_fresh()
    
    async def _fetch_sessions_fresh(self) -> List[Dict]:
        """Fetch fresh event data from Herkey"""
        
        logger.info("Fetching fresh event data")
        
        # Run scraping in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        sessions = await loop.run_in_executor(
            None, 
            lambda: self.scraper.scrape_sessions()
        )
        
        # Cache the results
        cache_key = "sessions_data"
        self.cache[cache_key] = {
            "data": sessions,
            "timestamp": datetime.now()
        }
        
        logger.info(f"Cached {len(sessions)} sessions")
        return sessions
    
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
    
    def _apply_event_filters(self, sessions: List[Dict], event_mode_filter: str, location_filter: Optional[str],
                           category_filter: Optional[str], price_filter: str, upcoming_only: bool) -> List[Dict]:
        """Apply filters to event list"""
        
        filtered_sessions = sessions
        
        # Filter by upcoming status
        if upcoming_only:
            filtered_sessions = [e for e in filtered_sessions if e.get("is_upcoming", True)]
        
        # Filter by event mode
        if event_mode_filter != "all":
            filtered_sessions = [
                event for event in filtered_sessions
                if event.get("mode", "unknown") == event_mode_filter
            ]
        
        # Filter by location
        if location_filter:
            filtered_sessions = [
                event for event in filtered_sessions
                if location_filter.lower() in event.get("location", "").lower()
            ]
        
        # Filter by category
        if category_filter:
            filtered_sessions = [
                event for event in filtered_sessions
                if any(category_filter.lower() in cat.lower() 
                      for cat in event.get("categories", []))
            ]
        
        # Filter by price
        if price_filter == "free":
            filtered_sessions = [
                event for event in filtered_sessions
                if event.get("is_free", False)
            ]
        elif price_filter == "paid":
            filtered_sessions = [
                event for event in filtered_sessions
                if not event.get("is_free", True)
            ]
        
        return filtered_sessions
    
    def _add_recommendation_scores(self, recommendations: List[Dict], candidate_profile: Dict) -> List[Dict]:
        """Add detailed scoring information to recommendations"""
        
        scored_recommendations = []
        for event in recommendations:
            # Calculate match reasons
            match_reasons = []
            
            # Check interest matches
            interests = [i.lower() for i in candidate_profile.get("interests", [])]
            event_categories = event.get("categories_lower", [])
            
            for interest in interests:
                if any(interest in cat for cat in event_categories):
                    match_reasons.append(f"Matches interest: {interest}")
            
            # Check mode preference
            preferred_mode = candidate_profile.get("preferred_event_mode", "").lower()
            if preferred_mode and event.get("mode") == preferred_mode:
                match_reasons.append(f"Matches preferred mode: {preferred_mode}")
            
            # Check if free (often preferred)
            if event.get("is_free", False):
                match_reasons.append("Free event")
            
            # Check if featured
            if event.get("featured", False):
                match_reasons.append("Featured event")
            
            event["match_reasons"] = match_reasons
            scored_recommendations.append(event)
        
        return scored_recommendations
    
    def _analyze_popular_categories(self, sessions: List[Dict]) -> Dict:
        """Analyze popular event categories"""
        all_categories = []
        for event in sessions:
            all_categories.extend(event.get("categories", []))
        
        category_counts = Counter(all_categories)
        
        return {
            "top_categories": [
                {"category": cat, "event_count": count}
                for cat, count in category_counts.most_common(15)
            ],
            "total_unique_categories": len(category_counts)
        }
    
    def _analyze_location_trends(self, sessions: List[Dict]) -> Dict:
        """Analyze location trends for offline sessions"""
        offline_sessions = [e for e in sessions if e.get("mode") == "offline"]
        location_counts = Counter(event.get("location", "Unknown") for event in offline_sessions)
        
        return {
            "top_locations": [
                {"location": loc, "event_count": count}
                for loc, count in location_counts.most_common(10)
            ],
            "total_offline_sessions": len(offline_sessions),
            "total_locations": len(location_counts)
        }
    
    def _analyze_mode_distribution(self, sessions: List[Dict]) -> Dict:
        """Analyze event mode distribution"""
        mode_counts = Counter(event.get("mode", "unknown") for event in sessions)
        total_sessions = len(sessions)
        
        distribution = [
            {
                "mode": mode,
                "event_count": count,
                "percentage": round((count / total_sessions) * 100, 1)
            }
            for mode, count in mode_counts.items()
        ]
        
        return {
            "distribution": sorted(distribution, key=lambda x: x["event_count"], reverse=True),
            "total_sessions": total_sessions
        }
    
    def _analyze_pricing(self, sessions: List[Dict]) -> Dict:
        """Analyze event pricing patterns"""
        free_sessions = sum(1 for e in sessions if e.get("is_free", False))
        paid_sessions = len(sessions) - free_sessions
        
        return {
            "free_sessions": free_sessions,
            "paid_sessions": paid_sessions,
            "free_percentage": round((free_sessions / len(sessions)) * 100, 1) if sessions else 0,
            "paid_percentage": round((paid_sessions / len(sessions)) * 100, 1) if sessions else 0
        }
    
    def _analyze_featured_sessions(self, sessions: List[Dict]) -> Dict:
        """Analyze featured sessions"""
        featured_sessions = [e for e in sessions if e.get("featured", False)]
        
        return {
            "featured_count": len(featured_sessions),
            "total_sessions": len(sessions),
            "featured_percentage": round((len(featured_sessions) / len(sessions)) * 100, 1) if sessions else 0,
            "featured_sessions": [
                {
                    "title": event.get("title"),
                    "categories": event.get("categories", []),
                    "mode": event.get("mode"),
                    "is_free": event.get("is_free", False)
                }
                for event in featured_sessions[:5]  # Top 5 featured sessions
            ]
        }
    
    def _analyze_time_patterns(self, sessions: List[Dict]) -> Dict:
        """Analyze time patterns in sessions"""
        # This is a basic implementation - you can enhance based on actual time data
        sessions_with_dates = [e for e in sessions if e.get("datetime_obj")]
        
        if not sessions_with_dates:
            return {"error": "No sessions with valid date information"}
        
        # Analyze by day of week
        day_counts = Counter(event["datetime_obj"].strftime("%A") for event in sessions_with_dates)
        
        # Analyze by month
        month_counts = Counter(event["datetime_obj"].strftime("%B") for event in sessions_with_dates)
        
        return {
            "day_of_week_distribution": [
                {"day": day, "event_count": count}
                for day, count in day_counts.most_common()
            ],
            "month_distribution": [
                {"month": month, "event_count": count}
                for month, count in month_counts.most_common()
            ]
        }
    
    def _organize_sessions_by_calendar(self, sessions: List[Dict], view: str, start_date: Optional[str]) -> Dict:
        """Organize sessions by calendar view"""
        calendar_data = {}
        
        for event in sessions:
            event_date = event.get("datetime_obj")
            if not event_date:
                continue
            
            date_key = event_date.strftime("%Y-%m-%d")
            
            if date_key not in calendar_data:
                calendar_data[date_key] = []
            
            calendar_data[date_key].append({
                "title": event.get("title"),
                "time": event.get("time"),
                "mode": event.get("mode"),
                "location": event.get("location"),
                "categories": event.get("categories", []),
                "is_free": event.get("is_free", False),
                "featured": event.get("featured", False)
            })
        
        return calendar_data
    
    def _extract_categories(self, sessions: List[Dict]) -> Dict:
        """Extract and count all categories"""
        all_categories = []
        for event in sessions:
            all_categories.extend(event.get("categories", []))
        
        category_counts = Counter(all_categories)
        
        return {
            "categories": [
                {"name": cat, "count": count}
                for cat, count in sorted(category_counts.items())
            ],
            "total_categories": len(category_counts),
            "total_sessions": len(sessions)
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
                    server_name="herkey-sessions-server",
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
    server = HerkeyEventsMCPServer()
    asyncio.run(server.run())

if __name__ == "__main__":
    main()