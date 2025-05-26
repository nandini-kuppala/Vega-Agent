import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from Agentic_ai.herkey_rag import get_job_recommendations

from Agentic_ai.herkey_rag import get_event_recommendations

from Agentic_ai.herkey_rag import get_session_recommendations

from Agentic_ai.herkey_rag import get_community_recommendations

from Agentic_ai.external_job_search import TavilyJobAgent
from Agentic_ai.carrer_guide import get_career_guidance

import streamlit as st

from backend.database import get_profile

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CareerGuidanceChatbot:
    """
    AI chatbot for career guidance, supporting starters, restarters, and raisers
    with personalized recommendations.
    """
    
    def __init__(self, firecrawl_api_key: str = None, groq_api_key: str = None):
        """Initialize the career guidance chatbot with API keys."""
        self.user_profile = None
        self.user_type = None  # "starter", "restarter", or "raiser"
        self.tavily_agent = TavilyJobAgent()
        
    
    def load_profile(self, user_id: str = None, profile_data: Dict = None) -> bool:
        """
        Load user profile either by ID (fetching from API) or directly from provided data.
        Returns True if profile loaded successfully, False otherwise.
        """
        if profile_data:
            self.user_profile = profile_data
            self._determine_user_type()
            return True
        
        if user_id:
            profile = get_profile(user_id)
            if profile:
                self.user_profile = profile
                self._determine_user_type()
                return True
            else:
                print("profile is not loaded")
        
        return False
    
    def _determine_user_type(self) -> None:
        """
        Determine if the user is a starter, restarter, or raiser based on profile data.
        """
        if not self.user_profile:
            return
        
        # Get experience years (handle different possible formats)
        experience_data = self.user_profile.get('experience_years', 6)
        if isinstance(experience_data, dict) and '$numberInt' in experience_data:
            exp_years = int(experience_data['$numberInt'])
        else:
            exp_years = int(experience_data) if experience_data else 5

        
        # Check for restarter (women who took a career break)
        life_stage = self.user_profile.get("life_stage", {})
        is_woman_with_break = False
        
        if life_stage.get("pregnancy_status") in ["Yes", "Recently"] or \
           life_stage.get("needs_flexible_work") is True or \
           "break" in life_stage.get("situation", "").lower():
            is_woman_with_break = True
        
        # Determine user type
        if is_woman_with_break:
            self.user_type = "restarter"
        elif exp_years >= 5:
            self.user_type = "raiser"
        else:
            self.user_type = "starter"
        
        logger.info(f"User determined to be a {self.user_type}")
    
    def process_query(self, query: str) -> str:
        """
        Process user query and generate a personalized response based on profile data.
        """
        if not self.user_profile:
            return "Please sign in so I can provide personalized career guidance based on your profile."
        
        # Normalize query for intent matching
        query_lower = query.lower().strip()
        
        # Job recommendations
        if any(kw in query_lower for kw in ["Latest Job Postings", "Latest Jobs"]):
            if "suggest" in query_lower or "recommend" in query_lower or "find" in query_lower:
                return self._get_job_recommendations()
            
        # Event recommendations
        if any(kw in query_lower for kw in ["event", "conference", "meetup", "gathering"]):
            if "suggest" in query_lower or "recommend" in query_lower or "upcoming" in query_lower:
                return self._get_event_recommendations()
        
        # Community recommendations
        if any(kw in query_lower for kw in ["community", "groups", "network", "communities"]):
            if "suggest" in query_lower or "recommend" in query_lower:
                return self._get_community_recommendations()
        
        # Learning session recommendations
        if any(kw in query_lower for kw in ["webinar", "workshop", "session", "upskilling programs"]):
            if "suggest" in query_lower or "recommend" in query_lower:
                return self._get_session_recommendations()
        
        # Post creation
        if any(kw in query_lower for kw in ["post", "share", "create content", "celebrate"]):
            purpose = None
            if "celebrat" in query_lower or "achievement" in query_lower:
                purpose = "celebrate"
            elif "experience" in query_lower or "perspective" in query_lower:
                purpose = "share"
            elif "ask" in query_lower or "question" in query_lower:
                purpose = "ask"
            elif "session" in query_lower or "conversation" in query_lower:
                purpose = "session"
            else:
                purpose = "share"
            
            return self._create_post(query, purpose)
        
        # General career guidance
        return self._get_general_career_guidance(query)
    
    def _get_job_recommendations(self) -> str:
        """Get personalized job recommendations from HerKey and external sources."""
        try:
            # Get recommendations from HerKey
            herkey_jobs = get_job_recommendations(self.user_profile)
            
            # Get external job recommendations 
            external_recommendations = {}
            if self.user_profile:
                tavily_result = self.tavily_agent.get_job_recommendations(self.user_profile)
                if tavily_result["status"] == "success":
                    external_recommendations = tavily_result
            #ccall th efuntions here for tavily suggested ext_jobs


            # Format response
            response = self._format_personalized_greeting()
            response += "\n\n### Job Recommendations Just For You\n\n"
            
            # Add HerKey jobs
            if herkey_jobs:
                response += "**From HerKey Platform:**\n\n"
                for i, job in enumerate(herkey_jobs[:3], 1):
                    response += f"{i}. **{job.get('job_title')}** at {job.get('company')}\n"
                    response += f"   - Match Score: {job.get('match_score')}/100\n"
                    response += f"   - Why: {job.get('match_explanation')}\n"
                    if job.get('job_url'):
                        response += f"   - [Apply Here]({job.get('job_url')})\n"
                    response += "\n"
            
            # Add external jobs from Tavily
            if external_recommendations and "recommendations" in external_recommendations:
                ext_jobs = external_recommendations["recommendations"]
                if ext_jobs:
                    response += "**From External Job Sites:**\n\n"
                    for i, job in enumerate(ext_jobs[:5], 1):  # Show top 5 results
                        response += f"{i}. **{job.get('job_title', 'Job Opportunity')}** at {job.get('company', 'Company')}\n"
                        response += f"   * Location: {job.get('location', 'Not specified')}\n"
                        
                        # Skills match
                        skills_match = job.get('skills_match', [])
                        if skills_match:
                            response += f"   * Skills Match: {', '.join(skills_match[:3])}\n"
                        
                        # Apply link
                        if job.get('job_link'):
                            response += f"   * [Apply Here]({job.get('job_link')})\n"
                        response += "\n"
            
            # Add user type specific advice
            if self.user_type == "starter":
                response += "\n**Starting Your Career:** As a recent graduate, focus on roles that provide strong mentorship and learning opportunities. Don't be discouraged if you don't meet 100% of the requirements - many employers value potential and enthusiasm in entry-level candidates.\n"
            elif self.user_type == "restarter":
                response += "\n**Restarting Your Career:** Your previous experience is valuable! Look for companies with returnship programs and highlight your transferable skills when applying. Many progressive employers recognize the unique perspectives that professionals returning to work bring to their teams.\n"
            else:  # raiser
                response += "\n**Advancing Your Career:** With your experience, look for roles that stretch your capabilities while building on your existing strengths. Consider how each opportunity aligns with your long-term career aspirations.\n"
            
            # Add call to action
            response += "\nWould you like me to help you prepare for interviews for any of these positions? Or would you prefer recommendations for learning resources to enhance your qualifications?"
            
            return response
        except Exception as e:
            logger.error(f"Error in job recommendations: {e}")
            return "I'm having trouble retrieving job recommendations right now. Let's try a different approach to your career development. Would you like to discuss upskilling opportunities or industry trends instead?"

    def _get_event_recommendations(self) -> str:
        """Get personalized event recommendations from HerKey."""
        try:
            events = get_event_recommendations(self.user_profile)
            
            response = self._format_personalized_greeting()
            response += "\n\n### Professional Events Tailored For You\n\n"
            
            if events:
                for i, event in enumerate(events[:3], 1):
                    response += f"{i}. **{event.get('event_title')}**\n"
                    response += f"   - Date: {event.get('event_date')}\n"
                    response += f"   - Match Score: {event.get('match_score')}/100\n"
                    response += f"   - Why It's Relevant: {event.get('match_explanation')}\n"
                    response += f"   - Expected Benefits: {event.get('expected_benefits')}\n"
                    if event.get('event_url'):
                        response += f"   - [Register Here]({event.get('event_url')})\n"
                    response += "\n"
            else:
                response += "I don't see any events that perfectly match your profile at the moment. However, here are some general recommendations:\n\n"
                response += "1. **Industry Conferences** - Great for networking and staying current with trends\n"
                response += "2. **Local Meetups** - More intimate settings to connect with peers\n"
                response += "3. **Virtual Workshops** - Convenient options to learn while balancing other commitments\n\n"
            
            # Add user type specific advice
            if self.user_type == "starter":
                response += "\nAs someone starting your career, events provide invaluable networking opportunities. When attending, prepare a brief introduction about yourself and your career interests. Don't hesitate to connect with speakers and other attendees!\n"
            elif self.user_type == "restarter":
                response += "\nEvents can be great for rebuilding your professional network after a career break. Many conferences now offer attendee matching services to help you connect with relevant professionals. Also look for events with returnship programs or dedicated sessions on career transitions.\n"
            else:  # raiser
                response += "\nWith your experience, consider events where you might not only learn but could potentially contribute as a panelist or speaker in the future. This visibility can open doors to new opportunities.\n"
            
            response += "\nWould you like tips on how to make the most of networking at these events?"
            
            return response
        except Exception as e:
            logger.error(f"Error in event recommendations: {e}")
            return "I'm having trouble retrieving event recommendations at the moment. Would you like to explore learning resources or community groups instead?"

    def _get_community_recommendations(self) -> str:
        """Get personalized community recommendations from HerKey."""
        try:
            communities = get_community_recommendations(self.user_profile)
            
            response = self._format_personalized_greeting()
            response += "\n\n### Communities That Will Help You Grow\n\n"
            
            if communities:
                for i, group in enumerate(communities[:3], 1):
                    response += f"{i}. **{group.get('group_name')}**\n"
                    response += f"   - Members: {group.get('member_count')}\n"
                    response += f"   - Match Score: {group.get('match_score')}/100\n"
                    response += f"   - Why Join: {group.get('match_explanation')}\n"
                    response += f"   - Networking Value: {group.get('networking_value')}\n"
                    if group.get('group_url'):
                        response += f"   - [Join Here]({group.get('group_url')})\n"
                    response += "\n"
            else:
                response += "I don't have specific community matches at the moment, but here are some types of groups that could benefit your career:\n\n"
                response += "1. **Professional Associations** in your field\n"
                response += "2. **Skill-Based Learning Groups** for peer development\n"
                response += "3. **Women in Tech/Business Networks** for support and mentorship\n\n"
            
            # Add some women-empowerment focused communities
            response += "**Women-Focused Professional Communities Worth Exploring:**\n\n"
            response += "- **Women Who Code** - Focused on career advancement for women in tech\n"
            response += "- **Elpha** - Community where women in tech connect and share advice\n"
            response += "- **Lean In Circles** - Small groups that meet regularly to support each other\n\n"
            
            # Add user type specific advice
            if self.user_type == "starter":
                response += "As a starter, communities provide invaluable support and guidance from those who've walked your path. Don't be shy about asking questions - most members are happy to help newcomers!\n"
            elif self.user_type == "restarter":
                response += "For women restarting their careers, communities can be a lifeline. Look for groups that specifically support professionals returning after a break - they often provide practical advice, moral support, and sometimes even job leads from understanding employers.\n"
            else:  # raiser
                response += "At your career stage, consider not just joining communities but taking leadership roles. Your experience is valuable, and mentoring others can be rewarding while expanding your professional network.\n"
            
            response += "\nWould you like tips on how to effectively engage in these communities?"
            
            return response
        except Exception as e:
            logger.error(f"Error in community recommendations: {e}")
            return "I'm having trouble accessing community information right now. Would you like to discuss career development strategies instead?"

    def _get_session_recommendations(self) -> str:
        """Get personalized learning session recommendations from HerKey."""
        try:
            sessions = get_session_recommendations(self.user_profile)
            
            response = self._format_personalized_greeting()
            response += "\n\n### Learning Sessions Perfect For Your Growth\n\n"
            
            if sessions:
                for i, session in enumerate(sessions[:3], 1):
                    response += f"{i}. **{session.get('session_title')}**\n"
                    response += f"   - Date: {session.get('session_date')}\n"
                    response += f"   - Host: {session.get('host')}\n"
                    response += f"   - Match Score: {session.get('match_score')}/100\n"
                    response += f"   - Why It's Valuable: {session.get('match_explanation')}\n"
                    response += f"   - Learning Outcomes: {session.get('learning_outcomes')}\n"
                    if session.get('session_url'):
                        response += f"   - [Register Here]({session.get('session_url')})\n"
                    response += "\n"
            else:
                response += "I don't have specific session recommendations at the moment, but based on your profile, these types of learning opportunities would benefit you:\n\n"
                
                # Customize based on profile skills
                skills = self.user_profile.get("skills", [])
                if any(s.lower() in ["ai", "ml", "dl", "nlp"] for s in skills):
                    response += "1. **Advanced AI Techniques** - Workshops covering the latest developments\n"
                    response += "2. **Practical ML Implementation** - Hands-on sessions with real-world applications\n"
                    response += "3. **AI Ethics and Responsible Development** - Critical knowledge for modern AI practitioners\n\n"
                elif any(s.lower() in ["wed development", "web development"] for s in skills):
                    response += "1. **Modern Frontend Frameworks** - React, Vue, or Angular deep-dives\n"
                    response += "2. **Backend Architecture** - Scalable and secure design patterns\n"
                    response += "3. **Full-Stack Integration** - Connecting all the pieces effectively\n\n"
                elif any(s.lower() in ["app deelopment", "app development"] for s in skills):
                    response += "1. **Mobile UX Design** - Creating intuitive user experiences\n"
                    response += "2. **Cross-Platform Development** - React Native or Flutter workshops\n"
                    response += "3. **App Performance Optimization** - Making your apps lightning fast\n\n"
                else:
                    response += "1. **Technical Skill Workshops** - Hands-on sessions to build practical expertise\n"
                    response += "2. **Industry Insight Webinars** - Learn from experienced professionals\n"
                    response += "3. **Career Development Seminars** - Strategic planning for your growth\n\n"
            
            # Add user type specific advice
            if self.user_type == "starter":
                response += "As you're beginning your career journey, focus on sessions that build fundamental skills while also exposing you to industry best practices. Take notes, ask questions, and try to implement what you learn in small projects.\n"
            elif self.user_type == "restarter":
                response += "After a career break, targeted learning sessions can help you quickly get up to speed on recent developments in your field. Look for intensive workshops and bootcamps specifically designed for professionals returning to work.\n"
            else:  # raiser
                response += "With your experience, consider advanced sessions that add specialized skills to your toolkit. Also valuable are leadership and management training that can help you transition to higher-level roles.\n"
            
            response += "\nWould you like help creating a personalized learning plan based on your career goals?"
            
            return response
        except Exception as e:
            logger.error(f"Error in session recommendations: {e}")
            return "I'm having trouble accessing learning session information right now. Would you like some general recommendations for skill development resources instead?"
    
    
    def _get_general_career_guidance(self, query: str) -> str:
        """Provide personalized career guidance based on user query and profile."""
        # Determine the basic intent of the query for more specific responses
        query_lower = query.lower()
        
        response = self._format_personalized_greeting()

        response = get_career_guidance(query_lower, self.user_profile)
        return response
    
    def _create_post(self, query: str, purpose: str) -> str:
        """Create a personalized post based on user query and profile information."""
        # Get profile information to personalize the post
        skills = self.user_profile.get("skills", [])
        job_title = self.user_profile.get("last_job", {}).get("title", "Professional")
        company = self.user_profile.get("last_job", {}).get("company", "")
        experience_years = self.user_profile.get("experience_years", 0)
        
        # Clean experience years if it's in MongoDB format
        if isinstance(experience_years, dict) and "$numberInt" in experience_years:
            experience_years = int(experience_years["$numberInt"])
        
        # Format as integer
        if isinstance(experience_years, str):
            try:
                experience_years = int(experience_years)
            except ValueError:
                experience_years = 0
                
        response = self._format_personalized_greeting()
        response += "\n\n### Your Personalized Post\n\n"
        
        # Create different types of posts based on purpose
        if purpose == "celebrate":
            response += "**Celebrating Achievement Post:**\n\n"
            response += "```\n"
            
            # Extract achievement details from query if available
            achievement = "recent achievement"
            if "promotion" in query.lower():
                achievement = "promotion"
            elif "certification" in query.lower():
                achievement = "new certification"
            elif "project" in query.lower():
                achievement = "successful project completion"
            elif "job" in query.lower():
                achievement = "new job offer"
                
            if self.user_type == "starter":
                response += f"🎉 Excited to share that I've achieved {achievement} in my early career journey!\n\n"
                response += f"As someone starting in {job_title if job_title != 'Professional' else 'my field'}, this milestone represents countless hours of learning and perseverance.\n\n"
                response += "I'm grateful for:\n"
                response += "✨ The mentors who guided me\n"
                response += "✨ The challenges that helped me grow\n"
                response += "✨ This supportive community\n\n"
                response += "What was your early career milestone that made you proud? I'd love to hear your stories!\n\n"
                response += "#CareerBeginnings #Achievement #ProfessionalGrowth"
            elif self.user_type == "restarter":
                response += f"🌟 Celebrating a special milestone today - {achievement} after returning to my professional journey!\n\n"
                response += f"Returning to work as a {job_title if job_title != 'Professional' else 'professional'} after a break has been both challenging and rewarding. This achievement feels especially meaningful.\n\n"
                response += "This journey reminded me that:\n"
                response += "💪 Career breaks build unique strengths\n"
                response += "💪 It's never too late to restart and thrive\n"
                response += "💪 Our diverse experiences add value\n\n"
                response += "To anyone restarting their career journey - your path is valid and valuable!\n\n"
                response += "#CareerRestart #WomenInWorkforce #ProfessionalComeback"
            else:  # raiser
                response += f"🏆 Thrilled to announce {achievement} as I continue advancing in my professional journey!\n\n"
                response += f"After {experience_years}+ years in {company if company else 'this industry'}, I'm still finding new ways to grow and contribute as a {job_title if job_title != 'Professional' else 'professional'}.\n\n"
                response += "This milestone reinforces my belief in:\n"
                response += "🚀 Continuous learning at every career stage\n"
                response += "🚀 Setting ambitious goals that push boundaries\n"
                response += "🚀 Building others up as we climb\n\n"
                response += "What recent professional achievement are you proud of? Let's celebrate our wins together!\n\n"
                response += "#CareerGrowth #ProfessionalDevelopment #LeadershipJourney"
            response += "```\n"
                
        elif purpose == "share":
            response += "**Sharing Experience Post:**\n\n"
            response += "```\n"
            
            # Extract experience details from query if available
            experience_topic = "recent experience"
            if "challenge" in query.lower() or "difficult" in query.lower():
                experience_topic = "overcoming a professional challenge"
            elif "lesson" in query.lower() or "learn" in query.lower():
                experience_topic = "valuable lesson I've learned"
            elif "advice" in query.lower() or "tip" in query.lower():
                experience_topic = "career advice I wish I'd received earlier"
                
            if self.user_type == "starter":
                response += f"📝 I wanted to share my thoughts on {experience_topic} as someone new to our industry.\n\n"
                response += f"As a {job_title if job_title != 'Professional' else 'new professional'}, I've discovered that success isn't just about technical skills—it's about adaptability, curiosity, and resilience.\n\n"
                response += "My key takeaways so far:\n"
                response += "💡 Asking questions isn't a weakness—it's how we grow\n"
                response += "💡 Finding the right mentor can transform your journey\n"
                response += "💡 Every mistake is an opportunity to improve\n\n"
                response += "What's one insight that helped you when you were starting out?\n\n"
                response += "#CareerBeginnings #ProfessionalGrowth #LessonsLearned"
            elif self.user_type == "restarter":
                response += f"🔄 Reflecting on {experience_topic} during my career restart journey.\n\n"
                response += f"Returning to work as a {job_title if job_title != 'Professional' else 'professional'} after a break has given me a unique perspective that combines my previous experience with fresh insights.\n\n"
                response += "What I've discovered:\n"
                response += "✨ The strengths we develop outside our careers enrich our professional lives\n"
                response += "✨ Confidence returns quickly when we focus on our transferable skills\n"
                response += "✨ Our unique journeys give us valuable perspectives\n\n"
                response += "Has anyone else returned to work after a break? What was your experience?\n\n"
                response += "#CareerComeback #ProfessionalRestart #WorkLifeIntegration"
            else:  # raiser
                response += f"🌱 After {experience_years}+ years in this field, I wanted to share some thoughts on {experience_topic}.\n\n"
                response += f"As I've advanced in my role as a {job_title if job_title != 'Professional' else 'professional'}, I've seen how our industry continues to evolve, and with it, the skills needed to thrive.\n\n"
                response += "Looking back, these principles have guided my growth:\n"
                response += "🔑 Technical excellence opens doors, but emotional intelligence helps you lead through them\n"
                response += "🔑 Building genuine relationships matters more than building your resume\n"
                response += "🔑 True expertise includes knowing when to unlearn outdated approaches\n\n"
                response += "I'd love to hear what principles have guided your professional development!\n\n"
                response += "#CareerWisdom #ProfessionalDevelopment #LeadershipInsights"
            response += "```\n"
                
        elif purpose == "ask":
            response += "**Question Post:**\n\n"
            response += "```\n"
            
            # Extract question topic from query if available
            question_topic = "career development"
            if "technology" in query.lower() or "tech" in query.lower():
                question_topic = "technology trends"
            elif "skill" in query.lower() or "learn" in query.lower():
                question_topic = "skill development"
            elif "balance" in query.lower() or "burnout" in query.lower():
                question_topic = "work-life balance"
                
            if self.user_type == "starter":
                response += f"❓ Seeking advice from this amazing community about {question_topic}!\n\n"
                response += f"As someone new in {job_title if job_title != 'Professional' else 'my career'}, I'm curious: How did you navigate the early stages of your professional journey?\n\n"
                response += "Specifically, I'd love to know:\n"
                response += "• What skills surprised you by being more important than you expected?\n"
                response += "• How did you find mentors who truly supported your growth?\n"
                response += "• What habits helped you learn and adapt quickly?\n\n"
                response += "Any advice or personal stories would be so appreciated! 🙏\n\n"
                response += "#CareerAdvice #EarlyCareerQuestions #ProfessionalGrowth"
            elif self.user_type == "restarter":
                response += f"🤔 Question for professionals who've taken career breaks: How did you approach {question_topic}?\n\n"
                response += f"I'm currently restarting my journey as a {job_title if job_title != 'Professional' else 'professional'} after some time away, and would value your insights.\n\n"
                response += "I'm particularly interested in:\n"
                response += "• Strategies for rebuilding confidence and momentum\n"
                response += "• Communicating the value of your break to potential employers\n"
                response += "• Balancing personal commitments with professional growth\n\n"
                response += "Thank you in advance for sharing your experiences! 💫\n\n"
                response += "#CareerRestart #ProfessionalAdvice #WomenInWorkforce"
            else:  # raiser
                response += f"📊 Poll for my network: What's your approach to {question_topic} as you advance in your career?\n\n"
                response += f"After {experience_years}+ years as a {job_title if job_title != 'Professional' else 'professional'}, I'm curious how others navigate this aspect of professional growth.\n\n"
                response += "In your experience, which factor has the biggest impact on career advancement?\n"
                response += "• Technical expertise and specialized knowledge\n"
                response += "• Leadership skills and team development\n"
                response += "• Strategic vision and business acumen\n"
                response += "• Network and relationship building\n\n"
                response += "I'd love to hear your reasoning in the comments! 🔍\n\n"
                response += "#CareerDevelopment #ProfessionalGrowth #LeadershipInsights"
            response += "```\n"
                
        elif purpose == "session":
            response += "**Session Post:**\n\n"
            response += "```\n"
            
            # Extract session topic from query if available
            session_topic = "professional development"
            if "technology" in query.lower() or "tech" in query.lower():
                session_topic = "emerging technologies"
            elif "skill" in query.lower() or "learn" in query.lower():
                session_topic = "essential skills for today's professionals"
            elif "balance" in query.lower() or "burnout" in query.lower():
                session_topic = "sustainable career growth and well-being"
                
            # Format date (3 days from now at 3pm)
            from datetime import datetime, timedelta
            session_date = datetime.now() + timedelta(days=3)
            formatted_date = session_date.strftime("%A, %B %d")
            formatted_time = "3:00 PM - 4:00 PM"
                
            if self.user_type == "starter":
                response += f"📣 JOIN ME FOR A CONVERSATION: \"{session_topic.title()} for New Professionals\"\n\n"
                response += f"🗓️ {formatted_date}\n"
                response += f"⏰ {formatted_time}\n\n"
                response += f"As someone navigating the early stages of my career in {job_title if job_title != 'Professional' else 'the professional world'}, I'm hosting a discussion about the challenges and opportunities we face as newcomers.\n\n"
                response += "In this session, we'll explore:\n"
                response += "• Building confidence while still learning\n"
                response += "• Finding mentorship and support\n"
                response += "• Developing both technical and soft skills\n\n"
                response += "This will be a supportive space to share experiences and strategies. I hope you'll join me!\n\n"
                response += "#CareerGrowth #ProfessionalDevelopment #VirtualSession"
            elif self.user_type == "restarter":
                response += f"📣 JOIN ME FOR A CONVERSATION: \"Restarting Your Career: {session_topic.title()}\"\n\n"
                response += f"🗓️ {formatted_date}\n"
                response += f"⏰ {formatted_time}\n\n"
                response += f"After taking time away and successfully returning to my role as a {job_title if job_title != 'Professional' else 'professional'}, I'm hosting a discussion about navigating career breaks and comebacks.\n\n"
                response += "We'll talk openly about:\n"
                response += "• Addressing gaps in your resume with confidence\n"
                response += "• Rebuilding your professional identity\n"
                response += "• Balancing work with personal priorities\n\n"
                response += "This session is for anyone contemplating a return to work, actively restarting, or interested in supporting returners.\n\n"
                response += "#CareerComeback #WomenInWorkforce #ProfessionalReentry"
            else:  # raiser
                response += f"📣 JOIN ME FOR A CONVERSATION: \"Advanced Career Strategies: {session_topic.title()}\"\n\n"
                response += f"🗓️ {formatted_date}\n"
                response += f"⏰ {formatted_time}\n\n"
                response += f"Drawing from {experience_years}+ years of experience as a {job_title if job_title != 'Professional' else 'professional'}, I'm hosting a strategic discussion on navigating the next levels of career growth.\n\n"
                response += "Topics we'll explore:\n"
                response += "• Transitioning from technical expert to strategic leader\n"
                response += "• Building and leveraging your professional influence\n"
                response += "• Creating opportunities for innovation and impact\n\n"
                response += "This session is perfect for mid-career professionals looking to intentionally shape their next career chapter.\n\n"
                response += "#LeadershipDevelopment #CareerStrategy #ProfessionalGrowth"
            response += "```\n"
                
        else:  # Default sharing post
            response += "**General Sharing Post:**\n\n"
            response += "```\n"
            response += f"✨ Reflecting on my journey as a {job_title if job_title != 'Professional' else 'professional'}...\n\n"
            response += "I've been thinking about how our careers are shaped not just by what we know, but by who we are and how we approach challenges.\n\n"
            response += "Three principles that have guided me:\n"
            response += "1️⃣ Continuous learning is non-negotiable\n"
            response += "2️⃣ Authentic connections create opportunities\n"
            response += "3️⃣ Resilience matters more than perfection\n\n"
            response += "What principles guide your professional journey? I'd love to hear your thoughts!\n\n"
            response += "#ProfessionalGrowth #CareerReflections #CommunityWisdom"
            response += "```\n"
            
        # Add tips for effective posting
        response += "\n**Tips to Maximize Your Post's Impact:**\n"
        response += "1. Best time to post: Weekday mornings or lunchtime for maximum visibility\n"
        response += "2. Engage with comments to boost your post's reach\n"
        response += "3. Consider adding a relevant image to increase engagement\n"
        response += "4. Follow up with commenters to build meaningful connections\n\n"
        response += "Would you like me to modify any part of this post before you share it?"
        
        return response
    
    def _format_personalized_greeting(self) -> str:
        """Create a personalized greeting based on user profile."""
        # Extract user information for personalization
        job_title = self.user_profile.get("last_job", {}).get("title", "")
        
        # Create appropriate greeting based on user type
        if self.user_type == "starter":
            return f"Hi there! As someone starting your career{' as a ' + job_title if job_title else ''}, here's some tailored guidance for you."
        elif self.user_type == "restarter":
            return f"Welcome back! As you restart your professional journey{' as a ' + job_title if job_title else ''}, I've put together some specific insights for you."
        else:  # raiser
            return f"Hello! Based on your experience{' as a ' + job_title if job_title else ''} and career goals, I've customized this guidance to help you advance further."


def main():
    """
    Main function to test the chatbot functionality.
    """
    
    # Initialize the chatbot
    chatbot = CareerGuidanceChatbot()
    
    # Sample profile data for testing
    sample_profile = {
        "_id": {"$oid": "6809c3daa03a7a1e240ab91f"},
        "user_id": "6809c002a03a7a1e240ab91e",
        "education": "Bachelor's Degree",
        "skills": ["Python", "Java", "AI", "NLP", "ML", "DL", "Wed Development", "App Development"],
        "current_status": "Looking for Work",
        "experience_years": {"$numberInt": "1"},
        "last_job": {"title": "AI Developer", "company": "OLVT"},
        "life_stage": {"pregnancy_status": "No", "needs_flexible_work": False, "situation": "None of the above"},
        "job_preferences": {
            "type": "Remote Work",
            "roles": ["Software"],
            "short_term_goal": "Upskill and crack good placement",
            "long_term_goal": "Yes, i want to be an enterpreneur"
        },
        "location": {"city": "Tirupati", "relocation": True, "work_mode": "Flexible"},
        "community": {"wants_mentorship": True, "mentorship_type": "Skill development", "join_events": True},
        "communication_preference": "Email",
        "consent": True,
        "created_at": {"$date": {"$numberLong": "1745470426051"}}
    }
    
    # Load the sample profile
    chatbot.load_profile(profile_data=sample_profile)
    
    # Test with a sample query
    sample_queries = [
        "Can you recommend some jobs for me?",
        "What skills should I focus on developing?",
        "Help me create a post to celebrate my new certification",
        "Are there any upcoming events I should attend?",
        "What communities would be good for me to join?"
    ]
    
    for query in sample_queries:
        print(f"\n\n=== Query: {query} ===\n")
        response = chatbot.process_query(query)
        print(response)


if __name__ == "__main__":
    main()