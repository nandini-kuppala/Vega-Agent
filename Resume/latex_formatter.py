class LaTeXResumeFormatter:
    """Formatter to convert resume content to LaTeX format following ATS-friendly template"""
    
    def __init__(self):
        """Initialize the LaTeX formatter"""
        pass
        
    def generate_latex(self, user_info, experience, education, projects, skills, achievements, publications=None, certifications=None):
        """Generate a LaTeX resume document based on user data"""
        
        # Start with the document preamble
        latex_content = self._generate_preamble()
        
        # Add document content
        latex_content += "\\begin{document}\n\n"
        
        # Add header with contact information
        latex_content += self._generate_header(user_info)
        
        # Add education section
        latex_content += self._generate_education(education)
        
        # Add experience section
        latex_content += self._generate_experience(experience)
        
        # Add projects section
        latex_content += self._generate_projects(projects)
        
        # Add skills section
        latex_content += self._generate_skills(skills)
        
        # Add achievements section if provided
        if achievements:
            latex_content += self._generate_achievements(achievements)
            
        # Add publications section if provided
        if publications:
            latex_content += self._generate_publications(publications)
            
        # Add certifications section if provided
        if certifications:
            latex_content += self._generate_certifications(certifications)
        
        # End the document
        latex_content += "\\end{document}"
        
        return latex_content
    
    def _generate_preamble(self):
        """Generate the LaTeX document preamble"""
        return """\\documentclass[letterpaper,11pt]{article}

\\usepackage{latexsym}
\\usepackage[empty]{fullpage}
\\usepackage{titlesec}
\\usepackage{marvosym}
\\usepackage[usenames,dvipsnames]{color}
\\usepackage{verbatim}
\\usepackage{enumitem}
\\usepackage[hidelinks]{hyperref}
\\usepackage{fancyhdr}
\\usepackage[english]{babel}
\\usepackage{tabularx}

% Use Times font
\\usepackage{times}

\\pagestyle{fancy}
\\fancyhf{} % clear all header and footer fields
\\fancyfoot{}
\\renewcommand{\\headrulewidth}{0pt}
\\renewcommand{\\footrulewidth}{0pt}

% Adjust margins for single page
\\addtolength{\\oddsidemargin}{-0.5in}
\\addtolength{\\evensidemargin}{-0.5in}
\\addtolength{\\textwidth}{1in}
\\addtolength{\\topmargin}{-.5in}
\\addtolength{\\textheight}{1.0in}

\\urlstyle{same}

\\raggedbottom
\\raggedright
\\setlength{\\tabcolsep}{0in}

% Sections formatting
\\titleformat{\\section}{
  \\vspace{-4pt}\\scshape\\raggedright\\large
}{}{0em}{}[\\color{black}\\titlerule \\vspace{-5pt}]

% Custom commands
\\newcommand{\\resumeItem}[1]{
  \\item\\small{
    {#1 \\vspace{-2pt}}
  }
}

\\newcommand{\\resumeSubheading}[4]{
  \\vspace{-2pt}\\item
    \\begin{tabular*}{0.97\\textwidth}[t]{l@{\\extracolsep{\\fill}}r}
      \\textbf{#1} & #2 \\\\
      \\textit{\\small#3} & \\textit{\\small #4} \\\\
    \\end{tabular*}\\vspace{-7pt}
}

\\newcommand{\\resumeProjectHeading}[2]{
    \\item
    \\begin{tabular*}{0.97\\textwidth}{l@{\\extracolsep{\\fill}}r}
      \\small#1 & #2 \\\\
    \\end{tabular*}\\vspace{-7pt}
}

\\newcommand{\\resumeSubItem}[1]{\\resumeItem{#1}\\vspace{-4pt}}

\\renewcommand\\labelitemii{$\\vcenter{\\hbox{\\tiny$\\bullet$}}$}

\\newcommand{\\resumeSubHeadingListStart}{\\begin{itemize}[leftmargin=0.15in, label={}]}
\\newcommand{\\resumeSubHeadingListEnd}{\\end{itemize}}
\\newcommand{\\resumeItemListStart}{\\begin{itemize}}
\\newcommand{\\resumeItemListEnd}{\\end{itemize}\\vspace{-5pt}}

"""
    
    def _generate_header(self, user_info):
        """Generate the resume header section with contact information"""
        name = user_info.get('name', '')
        email = user_info.get('email', '')
        phone = user_info.get('phone', '')
        linkedin = user_info.get('linkedin', '')
        github = user_info.get('github', '')
        location = user_info.get('location', '')
        
        # Basic header with name and contact info
        header = "\\begin{center}\n"
        header += f"    \\textbf{{\\Huge \\scshape {name}}} \\\\ \\vspace{{1pt}}\n"
        header += f"    \\small {phone} $|$\n"
        header += f"    \\href{{mailto:{email}}}{{{{{email}}}}} $|$ \n"
        
        # Add LinkedIn if available
        if linkedin:
            header += f"    \\href{{{linkedin}}}{{\\underline{{LinkedIn}}}} $|$\n"
            
        # Add GitHub if available
        if github:
            header += f"    \\href{{{github}}}{{\\underline{{GitHub}}}}"
            
        if location:
            header += f" $|$ {location}\n"
        else:
            header += "\n"
            
        header += "\\end{center}\n\n"
        
        return header
    
    def _generate_education(self, education_data):
        """Generate the education section of the resume"""
        # Start education section
        section = "\\section{Education}\n"
        section += "\\resumeSubHeadingListStart\n"
        
        # Parse education data
        if isinstance(education_data, str):
            # If education data is a string, split it into lines and process each line
            education_lines = education_data.strip().split('\n')
            for line in education_lines:
                if line.strip():
                    # Extract degree, institution, and year
                    parts = line.split(',')
                    if len(parts) >= 2:
                        institution = parts[0].strip()
                        degree = parts[1].strip()
                        location = ""
                        year = ""
                        gpa = ""
                        
                        if len(parts) >= 3:
                            year = parts[2].strip()
                        if len(parts) >= 4:
                            location = parts[3].strip()
                        if len(parts) >= 5:
                            gpa = parts[4].strip()
                            
                        section += f"    \\resumeSubheading\n"
                        section += f"      {{{institution}}}{{{location}}}\n"
                        section += f"      {{{degree} \\hfill \\textbf{{GPA:}} {gpa}}}{{{year}}}\n"
        else:
            # If education data is a dict or other format
            institution = education_data.get("institution", "")
            degree = education_data.get("degree", "")
            year = education_data.get("year", "")
            location = education_data.get("location", "")
            gpa = education_data.get("gpa", "")
            
            section += f"    \\resumeSubheading\n"
            section += f"      {{{institution}}}{{{location}}}\n"
            section += f"      {{{degree} \\hfill \\textbf{{GPA:}} {gpa}}}{{{year}}}\n"
        
        section += "\\resumeSubHeadingListEnd\n\n"
        return section
    
    def _generate_experience(self, experience_data):
        """Generate the work experience section of the resume"""
        section = "\\section{Experience}\n"
        section += "\\resumeSubHeadingListStart\n"
        
        # Parse experience data based on format
        if isinstance(experience_data, str):
            # Process as string with specific format
            experience_entries = experience_data.strip().split('\n\n')
            for entry in experience_entries:
                lines = entry.strip().split('\n')
                title = company = duration = location = ""
                responsibilities = []
                
                for line in lines:
                    line = line.strip()
                    if line.startswith("Title:"):
                        title = line.replace("Title:", "").strip()
                    elif line.startswith("Company:"):
                        company = line.replace("Company:", "").strip()
                    elif line.startswith("Duration:"):
                        duration = line.replace("Duration:", "").strip()
                    elif line.startswith("Location:"):
                        location = line.replace("Location:", "").strip()
                    elif line.startswith("Responsibilities"):
                        continue
                    elif line and not line.startswith("Title:") and not line.startswith("Company:"):
                        responsibilities.append(line)
                
                # Add experience entry
                section += f"\\resumeSubheading\n"
                section += f"{{{title} ({company})}}{{{duration}}}\n"
                if location:
                    section += f"{{{location}}}{{}}\n"
                else:
                    section += f"{{}}{{}}\n"
                
                # Add responsibilities as bullet points
                if responsibilities:
                    section += "\\vspace{-1em}\n\\resumeItemListStart\n"
                    for responsibility in responsibilities:
                        if responsibility.strip():
                            section += f"\\resumeItem{{{responsibility}}}\n"
                    section += "\\resumeItemListEnd\n"
                    section += "\\vspace{0.3em}\n\n"
        else:
            # Handle structured data format (dict, list, etc.)
            if isinstance(experience_data, list):
                for exp in experience_data:
                    title = exp.get('title', '')
                    company = exp.get('company', '')
                    duration = exp.get('duration', '')
                    location = exp.get('location', '')
                    responsibilities = exp.get('responsibilities', [])
                    
                    section += f"\\resumeSubheading\n"
                    section += f"{{{title} ({company})}}{{{duration}}}\n"
                    if location:
                        section += f"{{{location}}}{{}}\n"
                    else:
                        section += f"{{}}{{}}\n"
                    
                    # Add responsibilities as bullet points
                    if responsibilities:
                        section += "\\vspace{-1em}\n\\resumeItemListStart\n"
                        for responsibility in responsibilities:
                            if responsibility.strip():
                                section += f"\\resumeItem{{{responsibility}}}\n"
                        section += "\\resumeItemListEnd\n"
                        section += "\\vspace{0.3em}\n\n"
        
        section += "\\resumeSubHeadingListEnd\n\n"
        return section
    
    def _generate_projects(self, projects_data):
        """Generate the projects section of the resume"""
        section = "\\section{Projects}\n"
        section += "\\resumeSubHeadingListStart\n"
        
        # Process projects data
        if isinstance(projects_data, str):
            # If projects data is a string, split it into individual projects
            project_entries = projects_data.strip().split('\n\n')
            for entry in project_entries:
                lines = entry.strip().split('\n')
                if not lines:
                    continue
                    
                # First line is considered the project title
                title = lines[0].strip()
                link = ""
                
                # Extract link if it's in format "Title (Link: http://...)"
                if "Link:" in title:
                    title_parts = title.split("Link:")
                    title = title_parts[0].strip()
                    if len(title_parts) > 1:
                        link = title_parts[1].strip()
                
                # Process project details
                section += "\\resumeProjectHeading\n"
                if link:
                    section += f"{{\\textbf{{{title}}}}}{{\\hfill {{\\small \\textcolor{{blue}}{{\\href{{{link}}}{{Link}}}}}}}}\n"
                else:
                    section += f"{{\\textbf{{{title}}}}}{{\\hfill}}\n"
                
                # Add project details as bullet points
                if len(lines) > 1:
                    section += "\\resumeItemListStart\n"
                    for i in range(1, len(lines)):
                        if lines[i].strip():
                            section += f"\\resumeItem{{{lines[i].strip()}}}\n"
                    section += "\\resumeItemListEnd\n\n"
        else:
            # Handle structured data (list or dict)
            if isinstance(projects_data, list):
                for project in projects_data:
                    if isinstance(project, dict):
                        title = project.get('title', '')
                        link = project.get('link', '')
                        description = project.get('description', [])
                        
                        section += "\\resumeProjectHeading\n"
                        if link:
                            section += f"{{\\textbf{{{title}}}}}{{\\hfill {{\\small \\textcolor{{blue}}{{\\href{{{link}}}{{Link}}}}}}}}\n"
                        else:
                            section += f"{{\\textbf{{{title}}}}}{{\\hfill}}\n"
                        
                        # Add project details as bullet points
                        if description:
                            section += "\\resumeItemListStart\n"
                            if isinstance(description, list):
                                for item in description:
                                    section += f"\\resumeItem{{{item}}}\n"
                            else:
                                section += f"\\resumeItem{{{description}}}\n"
                            section += "\\resumeItemListEnd\n\n"
        
        section += "\\resumeSubHeadingListEnd\n\n"
        return section
    
    def _generate_skills(self, skills_data):
        """Generate the skills section of the resume"""
        section = "\\section{Skills}\n"
        section += "\\small{\n"
        section += "\\begin{itemize}[itemsep=0.1em]\n"
        
        # Process skills based on format
        if isinstance(skills_data, str):
            # If skills is a comma-separated string
            skills_list = [s.strip() for s in skills_data.split(',')]
            
            # Group skills by category
            section += f"    \\item \\textbf{{Programming Languages & Technologies}}: {', '.join(skills_list)}\n"
        
        elif isinstance(skills_data, list):
            # If skills is already a list
            section += f"    \\item \\textbf{{Programming Languages & Technologies}}: {', '.join(skills_data)}\n"
        
        elif isinstance(skills_data, dict):
            # If skills is organized by categories
            for category, skills in skills_data.items():
                if isinstance(skills, list):
                    section += f"    \\item \\textbf{{{category}}}: {', '.join(skills)}\n"
                else:
                    section += f"    \\item \\textbf{{{category}}}: {skills}\n"
        
        section += "\\end{itemize}\n"
        section += "}\n\n"
        return section
    
    def _generate_achievements(self, achievements_data):
        """Generate the achievements section of the resume"""
        section = "\\section{Achievements}\n"
        section += "\\resumeItemListStart\n"
        
        # Process achievements based on format
        if isinstance(achievements_data, str):
            # If achievements is a multi-line string
            achievements_list = achievements_data.strip().split('\n')
            for achievement in achievements_list:
                if achievement.strip():
                    section += f"\\resumeItem{{{achievement.strip()}}}\n"
        
        elif isinstance(achievements_data, list):
            # If achievements is already a list
            for achievement in achievements_data:
                if achievement.strip():
                    section += f"\\resumeItem{{{achievement.strip()}}}\n"
        
        section += "\\resumeItemListEnd\n\n"
        return section
    
    def _generate_publications(self, publications_data):
        """Generate the publications section of the resume"""
        section = "\\section{Publications}\n"
        section += "\\resumeItemListStart\n"
        
        # Process publications based on format
        if isinstance(publications_data, str):
            # If publications is a multi-line string
            publications_list = publications_data.strip().split('\n')
            for publication in publications_list:
                if publication.strip():
                    section += f"\\resumeItem{{{publication.strip()}}}\n"
        
        elif isinstance(publications_data, list):
            # If publications is already a list
            for publication in publications_data:
                if publication.strip():
                    section += f"\\resumeItem{{{publication.strip()}}}\n"
        
        section += "\\resumeItemListEnd\n\n"
        return section
    
    def _generate_certifications(self, certifications_data):
        """Generate the certifications section of the resume"""
        section = "\\section{Certifications}\n"
        section += "\\resumeItemListStart\n"
        
        # Process certifications based on format
        if isinstance(certifications_data, str):
            # If certifications is a multi-line string
            certifications_list = certifications_data.strip().split('\n')
            for certification in certifications_list:
                if certification.strip():
                    section += f"\\resumeItem{{{certification.strip()}}}\n"
        
        elif isinstance(certifications_data, list):
            # If certifications is already a list
            for certification in certifications_data:
                if certification.strip():
                    section += f"\\resumeItem{{{certification.strip()}}}\n"
        
        section += "\\resumeItemListEnd\n\n"
        return section
    

    def format(self, latex_content, user_profile):
        """
        Format the provided LaTeX content with proper template and styling.
        This is a compatibility method that either uses the provided LaTeX content
        or generates new content based on the user profile.
        
        Args:
            latex_content (str): LaTeX content to format
            user_profile (dict): User profile information
            
        Returns:
            str: Formatted LaTeX content
        """
        # If latex_content appears to be a complete LaTeX document, use it
        if "\\documentclass" in latex_content and "\\begin{document}" in latex_content:
            return latex_content
        
        # Otherwise, generate a new document using the user_profile
        experience = user_profile.get('experience', [])
        education = user_profile.get('education', [])
        skills = user_profile.get('skills', {})
        projects = ""  # We don't have projects in user_profile
        achievements = ""  # We don't have achievements in user_profile
        
        # Generate a LaTeX document from scratch
        return self.generate_latex(
            user_info=user_profile,
            experience=experience,
            education=education,
            projects=projects,
            skills=skills,
            achievements=achievements
        )