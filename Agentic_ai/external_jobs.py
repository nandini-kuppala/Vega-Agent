#external_jobs.py -- this file has functions that fetched jobs from differnet websites and recommend relevant ones to user
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from firecrawl import FirecrawlApp
import json
import os
from dotenv import load_dotenv
import groq
from datetime import datetime
# Load environment variables from .env file if it exists
load_dotenv()

class NestedModel1(BaseModel):
    """Schema for job posting data"""
    region: str = Field(description="Region or area where the job is located", default=None)
    role: str = Field(description="Specific role or function within the job category", default=None)
    job_title: str = Field(description="Title of the job position", default=None)
    experience: str = Field(description="Experience required for the position", default=None)
    job_link: str = Field(description="Link to the job posting", default=None)

class ExtractSchema(BaseModel):
    """Schema for job postings extraction"""
    job_postings: List[NestedModel1] = Field(description="List of job postings")

class JobRecommendation(BaseModel):    
    """Schema for job recommendation"""
    job_title: str = Field(description="Title of the job position")
    company: str = Field(description="Company offering the position")
    location: str = Field(description="Job location")
    experience_required: str = Field(description="Experience required for the position")
    skills_match: List[str] = Field(description="User skills that match the job requirements")
    missing_skills: List[str] = Field(description="Skills the user might need to develop")
    match_percentage: float = Field(description="Percentage match between user skills and job requirements")
    salary_estimate: str = Field(description="Estimated salary range")
    job_link: str = Field(description="Link to the job posting")
    recommendation_reason: str = Field(description="Reason why this job is recommended")

class UserJobRecommendations(BaseModel):
    """Schema for user job recommendations"""
    user_id: str = Field(description="User ID")
    timestamp: str = Field(description="Timestamp of recommendations")
    recommendations: List[JobRecommendation] = Field(description="List of job recommendations")


class JobHuntingAgent:
    """Agent responsible for finding jobs and providing recommendations based on user profile"""
    
    def __init__(self, firecrawl_api_key: str, groq_api_key: str, model_id: str = "llama3-70b-8192"):
        self.firecrawl = FirecrawlApp(api_key=firecrawl_api_key)
        self.groq_client = groq.Client(api_key=groq_api_key)
        self.model_id = model_id

    def _run_llm(self, prompt: str) -> str:
        """Run the Groq LLM with the given prompt"""
        try:
            response = self.groq_client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": "You are a career expert who helps find and analyze job opportunities based on user preferences."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=4000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error in _run_llm: {str(e)}")
            raise

    def extract_user_preferences(self, user_profile: Dict[str, Any]) -> Dict:
        """Extract job search preferences from user profile"""
        try:
            # Parse the user profile as a dictionary (fix access method)
            profile = user_profile
            
            # Default job category based on skills and last job
            job_category = "Software Development"
            if "skills" in profile and profile["skills"]:
                if "AI" in profile["skills"] or "ML" in profile["skills"] or "NLP" in profile["skills"]:
                    job_category = "Data Science"
                elif "wed development" in profile["skills"]: # Note: typo in original data
                    job_category = "Web Development"
                elif "app deelopment" in profile["skills"]: # Note: typo in original data
                    job_category = "Mobile App Development"
            
            # Extract job title preference
            if "last_job" in profile and profile["last_job"] and "title" in profile["last_job"]:
                job_title = profile["last_job"]["title"]
            elif "job_preferences" in profile and "roles" in profile["job_preferences"] and profile["job_preferences"]["roles"]:
                job_title = profile["job_preferences"]["roles"][0]
            else:
                job_title = "Software Developer"
                
            # Extract location preference
            if "location" in profile and "city" in profile["location"]:
                location = profile["location"]["city"]
                if profile["location"].get("relocation", False):
                    location += " (Open to relocation)"
            else:
                location = "Remote"
                
            # Determine if user wants remote work
            work_mode = "Remote"
            if "location" in profile and "work_mode" in profile["location"]:
                work_mode = profile["location"]["work_mode"]
                
            # Clean up skills (fix typos in the original data)
            cleaned_skills = []
            if "skills" in profile:
                for skill in profile["skills"]:
                    if skill == "wed development":
                        cleaned_skills.append("Web Development")
                    elif skill == "app deelopment":
                        cleaned_skills.append("App Development")
                    else:
                        cleaned_skills.append(skill)
                        
            return {
                "user_id": profile.get("user_id", "unknown"),
                "job_title": job_title,
                "location": location,
                "experience_years": profile.get("experience_years", 0),
                "skills": cleaned_skills,
                "education": profile.get("education", "Unknown"),
                "work_mode": work_mode,
                "job_category": job_category
            }
        except Exception as e:
            print(f"Error in extract_user_preferences: {str(e)}")
            return {
                "user_id": user_profile.get("user_id", "unknown"),
                "job_title": "Software Developer",
                "location": "Remote",
                "experience_years": user_profile.get("experience_years", 0),
                "skills": user_profile.get("skills", []),
                "education": user_profile.get("education", "Unknown"),
                "work_mode": "Remote",
                "job_category": "Software Development"
            }
    
    def find_jobs(self, user_preferences: Dict) -> List[Dict]:
        """Find jobs based on user preferences"""
        job_title = user_preferences["job_title"]
        location = user_preferences["location"].split(" (")[0]
        experience_years = user_preferences["experience_years"]
        skills = user_preferences["skills"]
        work_mode = user_preferences["work_mode"]
        
        formatted_job_title = job_title.lower().replace(" ", "-")
        formatted_location = location.lower().replace(" ", "-")
        skills_string = ", ".join(skills)
        
        include_remote = work_mode in ["Remote", "Flexible"]
        
        urls = [
            f"https://www.naukri.com/{formatted_job_title}-jobs-in-{formatted_location}",
            f"https://www.indeed.com/jobs?q={formatted_job_title}&l={formatted_location}",
            f"https://www.monster.com/jobs/search/?q={formatted_job_title}&where={formatted_location}"
        ]
        
        if include_remote:
            urls.append(f"https://www.indeed.com/jobs?q={formatted_job_title}&l=Remote")
            urls.append(f"https://www.monster.com/jobs/search/?q={formatted_job_title}&where=Remote")
        
        print(f"Searching for jobs with URLs: {urls}")
        
        try:
            prompt = f"""Extract job postings by region, roles, job titles, and experience from these job sites.
                    
                    Look for jobs that match these criteria:
                    - Job Title: Should be related to {job_title}
                    - Location: {location} {'or Remote' if include_remote else ''}
                    - Experience: Around {experience_years} years
                    - Skills: Should match at least some of these skills: {skills_string}
                    - Job Type: Full-time, Part-time, Contract, Temporary, Internship
                    
                    For each job posting, extract:
                    - region: The broader region or area where the job is located (e.g., "Northeast", "West Coast", "Midwest")
                    - role: The specific role or function (e.g., "Frontend Developer", "Data Analyst")
                    - job_title: The exact title of the job
                    - experience: The experience requirement in years or level (e.g., "3-5 years", "Senior")
                    - job_link: The link to the job posting
                    
                    IMPORTANT: Return data for at least 3 different job opportunities. MAXIMUM 15.
                    """
            
            schema = ExtractSchema.model_json_schema()
            
            raw_response = self.firecrawl.extract(
                urls=urls,
                prompt=prompt,
                schema=schema
            )
            print(raw_response)
            return raw_response  # Return empty list on exception
        except Exception as e:
            print(f"Error in find_jobs: {str(e)}")
            return [] 

    def analyze_job_matches(self, jobs, user_preferences: Dict) -> List[Dict]:
        """Analyze job matches based on user skills and preferences
        
        This function can handle either direct list of jobs or a raw API response
        """        
        
        prompt = f"""
        As a career expert, analyze these job opportunities for a specific user:

        Jobs Found:
        {jobs}

        User Profile:
        {user_preferences}

        INSTRUCTIONS:
        1. ONLY use the jobs from the jobs list - do not make up generic jobs
        2. From the raw api response provided, analyze each job for compatibility with the user's skills, experience, and preferences
        3. Select up to 5 jobs that best match the user's profile
        4. For each job, calculate a match percentage based on skills and experience
        5. Estimate a salary range for each job based on industry standards
        6. Provide a reason why each job is recommended
        7. List the user's skills that match the job requirements
        8. List any skills the user might need to develop for this role
        9. Make sure to include the exact job_link from the original job posting

        Return ONLY a valid JSON array with the following structure for each job:
        [
        {{
            "job_title": "String (use the exact job_title from the job posting)",
            "company": "String (extract from job description or URL if possible)",
            "location": "String (use the region from the job posting)",
            "experience_required": "String (use the experience from the job posting)",
            "skills_match": ["String", "String"...],
            "missing_skills": ["String", "String"...],
            "match_percentage": Number (0-100),
            "salary_estimate": "String",
            "job_link": "String (use the exact job_link from the job posting)",
            "recommendation_reason": "String"
        }},
        ...
        ]
        
        Return ONLY the JSON array, with no additional text.
        """
        
        try:
            response = self._run_llm(prompt)
            # Extract valid JSON from response
            response = response.strip()
            
            # Parse the response as JSON
            import json
            try:
                parsed_response = json.loads(response)
                return parsed_response  # Return the parsed JSON
            except json.JSONDecodeError as json_err:
                print(f"Failed to parse LLM response as JSON: {str(json_err)}")
                print(f"Raw response: {response}")
                # Return empty list on JSON parsing failure
                return []
                
        except Exception as e:
            print(f"Error in analyze_job_matches: {str(e)}")
            # Return empty list on exception
            return []
    
    def generate_recommendations(self, user_profile: Dict[str, Any]) -> Dict:
        """Generate job recommendations based on user profile"""
        try:
            # Extract user preferences from profile
            user_preferences = self.extract_user_preferences(user_profile)
            
            # Find jobs matching user preferences
            jobs = self.find_jobs(user_preferences)            
            
            # Analyze job matches
            job_recommendations = self.analyze_job_matches(jobs, user_preferences)
            
            # Ensure job_recommendations is a list
            if job_recommendations is None or not isinstance(job_recommendations, list):
                print(f"Warning: job_recommendations is not a list. Got {type(job_recommendations)}. Using empty list instead.")
                job_recommendations = []

            print(job_recommendations)
            
            # Create the final recommendations object
            recommendations = UserJobRecommendations(
                user_id=user_preferences["user_id"],
                timestamp=datetime.now().isoformat(),
                recommendations=job_recommendations
            )
            
            return recommendations.model_dump()
            
        except Exception as e:
            print(f"Error in generate_recommendations: {str(e)}")
            return {
                "error": str(e),
                "user_id": user_profile.get("user_id", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "recommendations": []
            }

def main():
    # Load API keys from environment variables
    firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
    groq_api_key = os.getenv("GROQ_API_KEY")
    
    if not firecrawl_api_key or not groq_api_key:
        print("Error: Missing API keys. Please set FIRECRAWL_API_KEY and GROQ_API_KEY environment variables.")
        return
    
    # Example user profile (in real implementation, this would come from MongoDB)
    user_profile = {
        "_id": {"$oid": "6809c3daa03a7a1e240ab91f"},
        "user_id": "6809c002a03a7a1e240ab91e",
        "education": "Bachelor's Degree",
        "skills": ["Python", "Java", "AI", "NLP ", "ML", "DL", "wed development", "app deelopment"],
        "current_status": "Looking for Work",
        "experience_years": 1,
        "last_job": {"title": "AI developer", "company": "OLVT"},
        "life_stage": {"pregnancy_status": "No", "needs_flexible_work": False, "situation": "None of the above"},
        "job_preferences": {
            "type": "Remote Work",
            "roles": ["Software"],
            "short_term_goal": "Upskill and crack good placement",
            "long_term_goal": "Yes, i want to be an enterpreneur "
        },
        "location": {"city": "Tirupati", "relocation": True, "work_mode": "Flexible"},
        "community": {"wants_mentorship": True, "mentorship_type": "Skill development", "join_events": True},
        "communication_preference": "Email",
        "consent": True,
        "created_at": {"$date": {"$numberLong": "1745470426051"}}
    }
    
    # Create job hunting agent
    agent = JobHuntingAgent(
        firecrawl_api_key=firecrawl_api_key,
        groq_api_key=groq_api_key,
        model_id="llama3-70b-8192" 
    )
    
    # Generate recommendations
    recommendations = agent.generate_recommendations(user_profile)
    
    # Output recommendations as JSON
    print(json.dumps(recommendations, indent=2))

if __name__ == "__main__":
    main()