import requests
from bs4 import BeautifulSoup
import re
import json
import html
import google.generativeai as genai
import streamlit as st

def scrape_linkedin_post(url):
    """
    Scrape LinkedIn post content using requests and format with Gemini AI
    
    Args:
        url (str): LinkedIn post URL
        
    Returns:
        dict: Contains success status, content, author, and message
    """
    
    # Clean and validate URL
    if not url or not isinstance(url, str):
        return {
            "success": False,
            "content": "",
            "author": "",
            "image_url": "",
            "message": "Invalid URL provided"
        }
    
    # Ensure URL is properly formatted
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Validate it's a LinkedIn URL
    if 'linkedin.com' not in url.lower():
        return {
            "success": False,
            "content": "",
            "author": "",
            "image_url": "",
            "message": "URL must be a LinkedIn post"
        }
    
    try:
        # Configure Gemini API
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        
        # Scrape LinkedIn post
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return {
                "success": False,
                "content": "",
                "author": "",
                "image_url": "",
                "message": f"Failed to access LinkedIn post. Status code: {response.status_code}"
            }
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract content from meta tags
        content = ""
        author = ""
        image_url = ""
        
        # Get content from Open Graph description
        og_description = soup.find('meta', property='og:description')
        if og_description:
            content = og_description.get('content', '')
        
        # Get author from Open Graph title
        og_title = soup.find('meta', property='og:title')
        if og_title:
            title_content = og_title.get('content', '')
            if ' on LinkedIn:' in title_content:
                author = title_content.split(' on LinkedIn:')[0].strip()
        
        # Get image URL
        og_image = soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image.get('content', '')
        
        # Try Twitter meta tags as fallback
        if not content:
            twitter_desc = soup.find('meta', name='twitter:description')
            if twitter_desc:
                content = twitter_desc.get('content', '')
        
        if not image_url:
            twitter_image = soup.find('meta', name='twitter:image')
            if twitter_image:
                image_url = twitter_image.get('content', '')
        
        # Look for JSON-LD structured data
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                if script.string:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        if 'author' in data and not author:
                            author_data = data['author']
                            if isinstance(author_data, dict) and 'name' in author_data:
                                author = author_data['name']
                        elif isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict) and 'author' in item and not author:
                                    author_data = item['author']
                                    if isinstance(author_data, dict) and 'name' in author_data:
                                        author = author_data['name']
                                    break
            except (json.JSONDecodeError, TypeError):
                continue
        
        # Clean and decode HTML entities
        if content:
            content = html.unescape(content)
            content = re.sub(r'\s+', ' ', content).strip()
        
        if author:
            author = html.unescape(author).strip()
        
        if not content and not author:
            return {
                "success": False,
                "content": "",
                "author": "",
                "image_url": "",
                "message": "Could not extract post content. LinkedIn may require authentication for this post."
            }
        
        # Format content with Gemini AI
        if content:
            formatted_content = format_content_with_gemini(content, author, model)
        else:
            formatted_content = f"Found this post informational:\n\n[Post content could not be extracted]\n\n-- Post by {author if author else 'Unknown'} on LinkedIn"
        
        return {
            "success": True,
            "content": formatted_content,
            "author": author,
            "image_url": image_url,
            "message": "Successfully extracted and formatted post content"
        }
        
    except Exception as e:
        return {
            "success": False,
            "content": "",
            "author": "",
            "image_url": "",
            "message": f"Error scraping LinkedIn post: {str(e)}"
        }

def format_content_with_gemini(raw_content, author, model):
    """
    Use Gemini AI to clean, format, and enhance the scraped content
    """
    try:
        prompt = f"""
Please clean and format this LinkedIn post content. Make it readable and professional:

Raw content: {raw_content}
Author: {author}

Instructions:
1. Fix any encoding issues and garbled text
2. Add appropriate emojis where they seem to be missing
3. Format numbered lists properly
4. Clean up HTML entities and special characters
5. Make the text flow naturally and professionally
6. Keep the original meaning intact
7. Format it as: "Found this post informational:" followed by the cleaned content, then "-- Post by [author] on LinkedIn"

Please return only the formatted content without any explanations.
"""
        
        response = model.generate_content(prompt)
        if response.text:
            return response.text.strip()
        else:
            return _fallback_format(raw_content, author)
            
    except Exception as e:
        # Fallback to basic formatting if Gemini fails
        return _fallback_format(raw_content, author)

def _fallback_format(content, author):
    """Fallback formatting if Gemini API fails"""
    try:
        # Basic text cleaning
        content = html.unescape(content)
        content = re.sub(r'&amp;', '&', content)
        content = re.sub(r'&lt;', '<', content)
        content = re.sub(r'&gt;', '>', content)
        content = re.sub(r'‚Äô', "'", content)
        content = re.sub(r'‚Ä¢', '•', content)
        content = re.sub(r'‚ù§', '👍', content)
        content = re.sub(r'üî•', '🚀', content)
        content = re.sub(r'Ô∏è‚É£', '', content)
        content = re.sub(r'\s+', ' ', content)
        
        # Format numbered lists
        content = re.sub(r'(\d+)\s*[-:]?\s*', r'\1. ', content)
        
        formatted_content = f"Found this post informational:\n\n{content.strip()}"
        
        if author:
            formatted_content += f"\n\n-- Post by {author} on LinkedIn"
        else:
            formatted_content += "\n\n-- Post from LinkedIn"
            
        return formatted_content
        
    except Exception:
        return f"Found this post informational:\n\n{content}\n\n-- Post by {author if author else 'Unknown'} on LinkedIn"

# Test function
def test_scraper():
    """Test the scraper with the provided URL"""
    test_url = "https://www.linkedin.com/posts/harisahmad59_ai-engineering-roadmap-activity-7332256848445693953-xVcv?utm_source=share&utm_medium=member_desktop&rcm=ACoAAD-hJ98B2I_cxCY8mZlqGiTsV0wtHQbTp2s"
    
    result = scrape_linkedin_post(test_url)
    
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    
    if result['success']:
        print(f"\nAuthor: {result['author']}")
        print(f"\nFormatted Content:\n{result['content']}")
        if result['image_url']:
            print(f"\nImage URL: {result['image_url']}")
    
    return result

# Example usage
if __name__ == "__main__":
    test_scraper()