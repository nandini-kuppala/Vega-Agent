# Asha AI 👩‍💼✨

 
**Empowering Women (Starters, Restarters, Raisers) on Their Career Journey** 🚀  

🔗 [App Link](https://ashacareerguide.streamlit.app/)


![Asha AI Banner](https://github.com/user-attachments/assets/7cf19f85-2998-42f3-9396-b0484fdaf66e)


---


## ✨ About Asha AI

Asha AI is a **multi-agent** chatbot system designed to **revolutionize career development and job searching for women**. It provides:

- 🎯 **Personalized career guidance**
    
- 🗓️ **Recommendations** for events, sessions, groups, and jobs from **HerKey.com**
    
- 🧩 **Agentic RAG** with **MCP** for up-to-date information retrieval from **HerKey** and external sources like **Naukri**, **Indeed**, **Monster**
    
- 🛠️ **Practical tools** like resume creation, skill assessment, career roadmapping
    
- 🌐 **Voice and multilingual support** in **9 Indian languages** and **English**
    

---

## 🏆 Unique Selling Points (USP)

- **🤖 Multi-Agent Intelligence**: Our specialized agent network provides deeper, more nuanced insights than traditional single-model approaches
    
- **🔍 Agentic RAG with MCP**: Combines precise retrieval of up-to-date information from Herkey with advanced generative AI capabilities
    
- **🗣️ Multilingual Support**: Accessible in 10 Indian languages via Sarvam AI, removing language barriers to career guidance
    
- **🛠️ End-to-End Career Companion**: Integrates multiple career tools in one cohesive platform (resume building, skill assessment, interview prep, and more)
    
- **📈 Continuous Learning Loop**: Improves over time through conversation analysis and reinforcement learning

---

## 🧩 System Architecture

![Architecture Diagram](https://github.com/user-attachments/assets/51645ab1-85bf-4767-9753-dfe994d2a4f6)

## 🧠 Memeory Management and Multi-turn Conversation Handling 🔄

![image](https://github.com/user-attachments/assets/8418b9e1-b5be-4c82-9728-49d6ae420a02)

---

## 💫 Features

### Core Features
    
- **🤝 Conversational Career Guidance**: Get personalized career advice through natural conversations
    
- **📝 Resume Builder**: Create ATS-friendly resumes customized for specific job applications
    
- **🔄 Personalized Recommendations**: Discover events, sessions, groups, and job opportunities tailored to your profile
    
- **🌐 Multilingual Voice Support**: Interact in your preferred language among 10 Indian languages

    
### Special Tools
    
- **📊 Skill Assessment**: Get detailed evaluation of your skills with actionable improvement recommendations
    
- **🛣️ Career Roadmapping**: Access customized learning paths for achieving your career goals
    
- **🎯 Job Match Analysis**: Evaluate how well your profile matches with specific job requirements
    
- **🎤 Interview Preparation**: Practice with AI-generated questions specific to your target roles


---

### ⚡⚡⚡**Conversation Context Management**⚡⚡⚡

- 🧠 Session summaries are generated and stored in Mongodb after each conversation.
    
- 🔍 A dedicated **Pattern Detection Agent** identifies trends in user queries for better personalization and feedback loops.
    
- All **user data** is securely encrypted and stored in **MongoDB**.

---
  
## 🔧 Tech Stack


- **Frontend**: ![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
    
- **Backend**: ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=FastAPI&logoColor=white) ![MongoDB](https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white)
    
- **AI Infrastructure**: ![LangChain](https://img.shields.io/badge/LangChain-0000FF?style=for-the-badge&logoColor=white) ![Pinecone](https://img.shields.io/badge/Pinecone-0000C0?style=for-the-badge&logoColor=white)
    
- **LLMs**: ![Gemini](https://img.shields.io/badge/Gemini-8E75B2?style=for-the-badge&logoColor=white) ![Groq](https://img.shields.io/badge/Groq-FF6B6B?style=for-the-badge&logoColor=white)
    
- **Voice**: ![Sarvam AI](https://img.shields.io/badge/Sarvam_AI-FFA500?style=for-the-badge&logoColor=white)


|🧩 Component|⚙️ Technology Used|
|---|---|
|🖥️ **Frontend**|[Streamlit](https://streamlit.io/)|
|⚡ **Backend**|[FastAPI](https://fastapi.tiangolo.com/)|
|🧠 **Agentic System**|[Crew AI](https://crewai.dev/), [LangChain](https://www.langchain.dev/), [Gemini API](https://deepmind.google/technologies/gemini/), [Groq](https://groq.com/)|
|🌐 **Web Scraping**|Custom Scraper + [Firecrawl](https://firecrawl.dev/)|
|🗄️ **Databases**|[MongoDB](https://www.mongodb.com/), [Pinecone](https://www.pinecone.io/)|
|🎙️ **Voice NLP**|[Sarvam AI](https://sarvam.ai/)|
|🧹 **Bias Detection**|Custom NLP Pipeline + Specialized Agent|

---


## 🧠 How It Works

    
### 🤖 Asha AI: Specialized Agent Orchestration

Asha AI operates through agent orchestration of specialized AI agents:

1. **👤 Profile Analyzer Agent**
    
   - Analyzes user profiles and questionnaire responses to understand career context
     
   - Creates a comprehensive user model to inform other agents' recommendations
     
   - Identifies skill gaps and career growth opportunities

2. **📅 Events & Sessions Agent**
    
   - Discovers relevant events and sessions from Herkey.com
     
   - Ranks opportunities based on user profile alignment and career goals
     
   - Provides personalized recommendations with clear reasoning
     

3. **👥 Groups Agent**
    
   - Identifies professional communities aligned with user interests and goals
     
   - Recommends networking opportunities to expand professional connections
     
   - Suggests industry-specific groups for knowledge sharing
     

4. **💼 Jobs Agent**
    
   - Searches multiple sources (Herkey, Naukari, Indeed, Monster) for relevant opportunities
     
   - Utilizes Firecrawl to maintain up-to-date job listings
     
   - Provides personalized job matches based on profile analysis

5. **🧭 Career Guide Agent**
    
   - Delivers tailored career advice and resources
     
   - Suggests upskilling opportunities aligned with career goals
     
   - Offers strategies for career transitions and growth
     

6. **📄 Resume Builder Agent**
    
   - Creates ATS-optimized resumes for specific job applications
     
   - Highlights relevant skills and experiences based on job descriptions
     
   - Suggests improvements to make resumes more competitive
     

7. **🛡️ Bias Detection & Quality Control Agent**
    
   - Ensures recommendations are unbiased and inclusive
     
   - Prevents hallucinations and maintains response quality
     
   - Guarantees relevant, accurate guidance



|Agent|Responsibilities|
|---|---|
|👤 **Profile Analyzer**|Analyze user profile, detect gaps, recommend growth|
|📅 **Events & Sessions Agent**|Recommend events aligned to career goals|
|👥 **Groups Agent**|Suggest professional groups for networking|
|💼 **Jobs Agent**|Provide personalized job opportunities|
|🧭 **Career Guide Agent**|Offer tailored career advice|
|📄 **Resume Builder Agent**|Build optimized, customized resumes|
|🛡️ **Bias Detection Agent**|Ensure fairness, accuracy, and inclusiveness|

---


## Process Flow Diagrams
![image](https://github.com/user-attachments/assets/57bc08fa-7b42-419f-976b-3410f52ab0f7)
    
![image](https://github.com/user-attachments/assets/a969df4a-3362-47f8-9e15-baa48b2c82f2)
    
![image](https://github.com/user-attachments/assets/dcb112de-c462-46c5-816e-f755a58dc163)
    
![image](https://github.com/user-attachments/assets/1fb55873-cd7a-439e-91f3-e85696cbcde4)


---


### 🔄 Workflow

1. **User Registration**: New users complete a comprehensive profile questionnaire
    
2. **Profile Analysis**: The Profile Analyzer Agent processes user information to understand needs
    
3. **Personalized Experience**: All recommendations and guidance are tailored based on profile analysis
    
4. **Continuous Improvement**: Session summaries and pattern analysis enhance future interactions

## 📊 Data Processing Flow

1. 📥 **Data Collection** (Herkey + Firecrawl Scraping)
    
2. 🧠 **Vectorization** (Pinecone Storage)
    
3. 🔍 **Retrieval** (Agentic RAG + MCP)
    
4. 🧠 **Generation** (Gemini, Groq)
    
5. ✅ **Quality Assurance** (Bias detection pipeline)


---
    
## 🔒 Security Features

Asha AI implements multiple security layers to protect user data:

- 🔐 **Encrypted MongoDB Storage**
    
- 🛑 **Strict Access Control**
        
- 🧹 **Regular Data Cleaning**
    
- 👁️ **Clear Transparency and Privacy Policies**
    

---

## 📊 Skill Assessment System
![image](https://github.com/user-attachments/assets/5ce3aba9-2841-4c5c-a6e1-4ed342d8f18f)

### Steps:

- 📄 **Resume Analysis**
    
- 🧩 **Job Description Matching**
    
- 📈 **Skill Rating and Gap Analysis**
    
- 🎤 **Interview Preparation (customized)**
    
- 🎯 **Skill Improvement Suggestions**


## 🚀 Our Comprehensive Skill Assessment System

1. 📄 **Resume Analysis**: AI agents analyze your resume to identify strengths and weaknesses.
    
2. 🧩 **Job Description Matching**: Evaluates how well your profile matches specific job requirements.
    
3. 📊 **Skill Rating**: Quantifies skill proficiency based on projects, achievements, and experience.
    
4. 🎯 **Interview Question Generation**: Creates targeted practice questions for interview preparation.
    
5. 🔧 **Improvement Recommendations**: Suggests specific actions to enhance your competitive edge.
    

---


## 🌐 Multilingual Support

Asha AI breaks language barriers by supporting 10 Indian languages:

- Hindi
- Bengali
- Telugu
- Tamil
- Marathi
- Gujarati
- Kannada
- Malayalam
- Punjabi
- English

Voice input and output are handled through Sarvam AI's advanced transcription and translation capabilities.

---

## 🚀 Performace
![image](https://github.com/user-attachments/assets/8afc24f7-496e-428f-bab6-e461e471a203)
![image](https://github.com/user-attachments/assets/aee15e12-1ab1-43fc-91fb-3428e7b3c5df)
![image](https://github.com/user-attachments/assets/0a01d830-8470-49b0-afa9-00b268718290)
![image](https://github.com/user-attachments/assets/04617a91-72f9-4605-875b-b47a7df9f620)
![image](https://github.com/user-attachments/assets/3f8636a7-19f5-4b29-a870-c4c1f59aae3d)

![image](https://github.com/user-attachments/assets/9b484354-3f82-4de4-a3e5-69f14ac56b9f)
![image](https://github.com/user-attachments/assets/4368565f-5e49-49af-aac6-569139248d3b)

---
# 🎉 Let's Build Empowered Careers Together!

## 🚀 Future Roadmap

### 📈 Personal Development Analytics

- Dashboard showing progress metrics 📊
    
- Track improvement over time ⏳
    

### 🗺️ Interactive Career Path Visualization

- 3D visualization of potential career paths 🧭
    
- Explore decision points and skill requirements 🎯
    

### 🎥 Video Interview Simulation

- AI-powered mock interviews 🤖
    
- Instant feedback and recording capabilities 📼
    

### 🧑‍🏫 Mentor Matching System

- Connect with relevant industry professionals 🤝
    
- Tailored to your career goals 🎓
    

### 🌐 Distributed Agent Architecture

- Scalable to handle 50,000+ concurrent users ⚡
    

### 🧠 Advanced Contextual Understanding

- Deep comprehension of career nuances 🏢
    
- Master industry-specific terminology 📚
    

### 📚 Skill Development Progression

- Measure and visualize growth in user capabilities 📈
    
- Personalized learning journey 🛤️
    

# 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

Built with ❤️ to empower women in their professional journeys.


👥 Contributor
Nandini Kuppala
