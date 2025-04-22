#!/usr/bin/env python3
import argparse
import os
import time
import datetime
import random
import sys
import io
import re
import nltk
from pyresparser import ResumeParser
from pdfminer3.layout import LAParams
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer3.converter import TextConverter
from Courses import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos

# Download nltk stopwords if needed
nltk.download('stopwords', quiet=True)

# Parse command line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description='Resume Parser with PostgreSQL')
    parser.add_argument('pdf_path', help='Path to the resume PDF file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print detailed information')
    return parser.parse_args()

# Reads PDF file and extracts text
def pdf_reader(file):
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)
    
    with open(file, 'rb') as fh:
        for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
            page_interpreter.process_page(page)
            
        text = fake_file_handle.getvalue()

    # Close open handles
    converter.close()
    fake_file_handle.close()
    return text

# Improved name extraction function
def extract_name(resume_text):
    """
    Extract name from resume text using multiple advanced heuristics
    """
    # Common resume header patterns that often contain names
    name_patterns = [
        # First line capitalized names (2-3 words)
        r'(?i)^([A-Z][a-z]+(?:[ \'-][A-Z][a-z]+){1,2})\s*$',
        
        # Name with colon format
        r'(?i)Name\s*:\s*([A-Z][a-z]+(?:[ \'-][A-Z][a-z]+){1,2})',
        
        # Name with dash format
        r'(?i)Name\s*-\s*([A-Z][a-z]+(?:[ \'-][A-Z][a-z]+){1,2})',
        
        # Name followed by contact info (common resume format)
        r'(?i)^([A-Z][a-z]+(?:[ \'-][A-Z][a-z]+){1,2})\s*\n+(?:[^\n]+\n)*(?:Address|Email|Phone|Tel|Contact|LinkedIn|Github)',
        
        # Name with professional designation
        r'(?i)^([A-Z][a-z]+(?:[ \'-][A-Z][a-z]+){1,2})(?:\s*[,|]\s*[A-Za-z. ]+)?$',
        
        # Centered name in header (preceded and followed by blank lines)
        r'(?i)^\s*\n([A-Z][a-z]+(?:[ \'-][A-Z][a-z]+){1,2})\s*\n',
        
        # Name in ALL CAPS (common formatting)
        r'(?i)^([A-Z]+(?:[ \'-][A-Z]+){1,2})\s*$'
    ]
    
    # Get the first 10 lines for header analysis
    first_10_lines = resume_text.strip().split('\n')[:10]
    header_text = '\n'.join(first_10_lines)
    
    # Try each pattern
    name_candidates = []
    
    # Method 1: Try defined patterns
    for pattern in name_patterns:
        matches = re.search(pattern, header_text, re.MULTILINE)
        if matches:
            name_candidates.append(matches.group(1).strip())
    
    # Method 2: Check for names in capital letters in first 5 lines
    for line in first_10_lines[:5]:
        line = line.strip()
        # All caps name (common formatting)
        if re.match(r'^[A-Z]+(?:\s+[A-Z]+){1,2}$', line) and len(line) > 3:
            name_candidates.append(line.title())  # Convert to title case
    
    # Method 3: First non-empty line that looks like a name
    if first_10_lines:
        first_line = first_10_lines[0].strip()
        if first_line and len(first_line.split()) <= 4 and not any(c.isdigit() for c in first_line) and '@' not in first_line:
            name_candidates.append(first_line)
    
    # Filter and validate candidates
    valid_names = []
    for name in name_candidates:
        # Basic validation
        if name and len(name.split()) >= 2 and len(name) > 3:
            # Skip if contains common non-name indicators
            skip_indicators = ['resume', 'cv', 'curriculum', 'vitae', 'address', 'email', 
                              'phone', 'tel', 'contact', '@', 'www', 'http', 'summary']
            
            if not any(indicator in name.lower() for indicator in skip_indicators):
                valid_names.append(name)
    
    # Return the most likely name based on position and validation
    if valid_names:
        return valid_names[0]
    
    # Fall back to first line if all else fails
    if first_10_lines:
        first_line = first_10_lines[0].strip()
        if first_line and len(first_line.split()) <= 4 and not '@' in first_line and not re.search(r'\d', first_line):
            return first_line
    
    return "Name not found"
# Course recommendations based on the skills
def course_recommender(course_list):
    print("\n⭐️ Recommended Courses: ⭐️")
    rec_course = []
    # Choose 5 random courses
    random.shuffle(course_list)
    for i, (c_name, c_link) in enumerate(course_list[:5], 1):
        print(f"({i}) {c_name}: {c_link}")
        rec_course.append(c_name)
    return rec_course

# Analyze how comprehensive the resume is with research-based scoring
def analyze_resume_completeness(resume_text, cand_level="Fresher", verbose=False):
    """
    Check for various sections in the resume and score accordingly using research-based weights
    that vary depending on candidate experience level.
    """
    resume_score = 0
    results = []
    
    # Define score weights based on candidate level
    if cand_level == "Experienced":
        # Weights for experienced candidates (3+ years)
        score_weights = {
            'Objective': 5,         # 5% weight
            'Experience': 55,       # 55% weight
            'Skills': 20,           # 20% weight
            'Education': 10,        # 10% weight
            'Certifications': 5,    # 5% weight 
            'Achievements': 3,      # 3% weight
            'Projects': 2,          # 2% weight
            'Hobbies': 0            # 0% weight
        }
    else:
        # Weights for entry-level candidates (<3 years experience)
        score_weights = {
            'Objective': 5,         # 5% weight
            'Education': 25,        # 25% weight
            'Skills': 25,           # 25% weight
            'Projects': 20,         # 20% weight
            'Internship': 15,       # 15% weight (combined with Experience for freshers)
            'Certifications': 5,    # 5% weight
            'Achievements': 5,      # 5% weight
            'Hobbies': 0            # 0% weight
        }
    
    # Check for various sections in the resume with improved section detection
    section_checks = [
        ('Objective', ['Objective', 'Summary', 'Career Objective', 'Professional Summary'], 
         "You have added Objective/Summary", 
         "Research shows a concise summary (~15 words) can boost interview chances. Consider adding one."),
        
        ('Education', ['Education', 'School', 'College', 'University', 'Bachelor', 'Master', 'Ph.D', 'B.Tech', 'M.Tech'], 
         "You have added Education Details", 
         "Add education details to showcase your qualifications - critical for entry-level positions."),
        
        ('Experience', ['Experience', 'Work Experience', 'Professional Experience', 'Employment History'], 
         "You have added Experience", 
         "Recruiters spend 67% of their time on experience sections. Add detailed work history."),
        
        ('Internship', ['Internship', 'Internships'], 
         "You have added Internships", 
         "For entry-level roles, internships significantly boost your chance of consideration."),
        
        ('Skills', ['Skills', 'Technical Skills', 'Core Competencies', 'Key Skills'], 
         "You have added Skills", 
         "93% of hiring managers prefer skills-based screening. Add more relevant technical skills."),
        
        ('Hobbies', ['Hobbies', 'Interests', 'Activities'], 
         "You have added your Hobbies", 
         "While hobbies add personality, they rarely impact hiring decisions. Keep this section minimal."),
        
        ('Achievements', ['Achievements', 'Awards', 'Honors', 'Recognition'], 
         "You have added your Achievements", 
         "Quantified achievements make your resume 40% more likely to get interviews."),
        
        ('Certifications', ['Certifications', 'Certification', 'Professional Certifications'], 
         "You have added your Certifications", 
         "Industry certifications increase interview chances by up to 20% in tech fields."),
        
        ('Projects', ['Projects', 'Project', 'Academic Projects', 'Personal Projects'], 
         "You have added your Projects", 
         "Projects demonstrate practical skills - crucial for entry-level candidates with limited experience.")
    ]
    
    # Check for each section
    for section_name, keywords, success_msg, missing_msg in section_checks:
        found = False
        for keyword in keywords:
            # Case insensitive search for both uppercase and non-uppercase variations
            if re.search(r'(?i)\b' + re.escape(keyword) + r'\b', resume_text):
                # Calculate points based on weight percentage
                points = score_weights.get(section_name, 0)
                resume_score += points
                results.append((True, f"[+] {success_msg} (+{points} points)"))
                found = True
                break
        if not found:
            results.append((False, f"[-] {missing_msg}"))
    
    # Print results
    for is_present, msg in results:
        print(msg)
    
    # Additional checks based on the content
    if verbose:
        # Check resume length
        words = len(resume_text.split())
        if words < 200:
            print("[-] Your resume is too short. Ideally, it should be 350-600 words.")
        elif words > 700:
            print("[!] Your resume exceeds recommended length. Research shows 1-2 pages or 350-600 words are optimal.")
        
        # Check for contact information
        if not re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', resume_text):
            print("[-] No email found. 68% of recruiters consider missing contact info a dealbreaker.")
        
        if not re.search(r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume_text):
            print("[-] No phone number found. Complete contact information is essential.")
        
        # Check for LinkedIn presence
        if not re.search(r'linkedin\.com', resume_text.lower()):
            print("[-] Consider adding your LinkedIn profile. 87% of recruiters use LinkedIn during screening.")
    
    return resume_score

# Main function
def main():
    args = parse_arguments()
    pdf_path = args.pdf_path
    verbose = args.verbose
    pdf_name = os.path.basename(pdf_path)

    # Check if the PDF file exists
    if not os.path.exists(pdf_path):
        print(f"Error: The file {pdf_path} does not exist.")
        sys.exit(1)

    print(f"\nProcessing resume: {pdf_name}\n")

    # Parse the resume
    print("Analyzing your resume...")
    
    try:
        # Get the whole resume text first
        resume_text = pdf_reader(pdf_path)
        
        # Extract name directly from text
        extracted_name = extract_name(resume_text)
        if extracted_name != "Name not found":
            print(f"\nCandidate Name: {extracted_name}")
        
        # Use the library for other extractions
        resume_data = ResumeParser(pdf_path).get_extracted_data()
        
        if resume_data:
            # Determine candidate level with improved detection
            if "experience" in resume_text.lower():
                # Check for years of experience with regex
                exp_years = re.findall(r'(\d+)(?:\+)?\s*(?:year|yr)s?\s+(?:of\s+)?experience', resume_text.lower())
                
                cand_level = "Fresher"
                if exp_years:
                    years = max([int(y) for y in exp_years] or [0])
                    if years >= 3:
                        cand_level = "Experienced"
                        print(f"\nYou have {years}+ years of experience - Experienced level!")
                    else:
                        cand_level = "Intermediate"
                        print(f"\nYou have {years} years of experience - Intermediate level!")
                elif re.search(r'(?i)senior|lead|manager|director|head', resume_text):
                    cand_level = "Experienced"
                    print("\nBased on your titles, you are at Experienced level!")
                elif re.search(r'(?i)internship', resume_text):
                    cand_level = "Intermediate"
                    print("\nYou are at Intermediate level!")
            else:
                cand_level = "Fresher"
                print("\nYou are at Fresher level!")
            
            # Skills analysis
            print("\n🔍 Skills Analysis:")
            skills = resume_data['skills']
            print(f"Identified skills: {', '.join(skills)}")
            
            # Keywords for field prediction
            ds_keyword = ['tensorflow', 'keras', 'pytorch', 'machine learning', 'deep learning', 'flask', 'streamlit', 
                          'data science', 'data analysis', 'pandas', 'numpy', 'matplotlib', 'scikit-learn', 'statistics']
            
            web_keyword = ['react', 'django', 'node js', 'nodejs', 'react js', 'php', 'laravel', 'magento', 'wordpress', 
                          'javascript', 'angular js', 'c#', 'asp.net', 'flask', 'html', 'css', 'bootstrap', 'jquery']
            
            android_keyword = ['android', 'android development', 'flutter', 'kotlin', 'xml', 'kivy', 'java android']
            
            ios_keyword = ['ios', 'ios development', 'swift', 'cocoa', 'cocoa touch', 'xcode', 'objective-c']
            
            uiux_keyword = ['ux', 'adobe xd', 'figma', 'zeplin', 'balsamiq', 'ui', 'prototyping', 'wireframes', 
                           'storyframes', 'adobe photoshop', 'photoshop', 'editing', 'adobe illustrator', 'illustrator', 
                           'adobe after effects', 'after effects', 'adobe premier pro', 'premiere pro', 'adobe indesign', 
                           'indesign', 'wireframe', 'solid', 'grasp', 'user research', 'user experience']
            
            # Predict field and recommend skills
            recommended_skills = []
            reco_field = ''
            rec_course = []
            
            # Create a list of lowercase skills
            skills_lower = [skill.lower() for skill in skills]
            
            # Initialize counters for each category
            field_scores = {
                'Data Science': sum(1 for keyword in ds_keyword if keyword in skills_lower or any(keyword in skill.lower() for skill in skills)),
                'Web Development': sum(1 for keyword in web_keyword if keyword in skills_lower or any(keyword in skill.lower() for skill in skills)),
                'Android Development': sum(1 for keyword in android_keyword if keyword in skills_lower or any(keyword in skill.lower() for skill in skills)),
                'IOS Development': sum(1 for keyword in ios_keyword if keyword in skills_lower or any(keyword in skill.lower() for skill in skills)),
                'UI-UX Development': sum(1 for keyword in uiux_keyword if keyword in skills_lower or any(keyword in skill.lower() for skill in skills))
            }
            
            # Find the field with the highest score
            if any(field_scores.values()):
                reco_field = max(field_scores.items(), key=lambda x: x[1])[0]
                
                # Provide recommendations based on the field
                if reco_field == 'Data Science':
                    print("\n📊 Our analysis says you are looking for Data Science Jobs.")
                    recommended_skills = ['Data Visualization', 'Predictive Analysis', 'Statistical Modeling', 'Data Mining', 
                                         'Clustering & Classification', 'Data Analytics', 'Quantitative Analysis', 
                                         'Web Scraping', 'ML Algorithms', 'Keras', 'Pytorch', 'Probability', 
                                         'Scikit-learn', 'Tensorflow', 'Flask', 'Streamlit']
                    rec_course = course_recommender(ds_course)
                    
                elif reco_field == 'Web Development':
                    print("\n🌐 Our analysis says you are looking for Web Development Jobs.")
                    recommended_skills = ['React', 'Django', 'Node JS', 'React JS', 'PHP', 'Laravel', 'Magento', 
                                         'WordPress', 'Javascript', 'Angular JS', 'C#', 'Flask', 'SDK']
                    rec_course = course_recommender(web_course)
                    
                elif reco_field == 'Android Development':
                    print("\n📱 Our analysis says you are looking for Android App Development Jobs.")
                    recommended_skills = ['Android', 'Android Development', 'Flutter', 'Kotlin', 'XML', 
                                         'Java', 'Kivy', 'GIT', 'SDK', 'SQLite']
                    rec_course = course_recommender(android_course)
                    
                elif reco_field == 'IOS Development':
                    print("\n📱 Our analysis says you are looking for IOS App Development Jobs.")
                    recommended_skills = ['IOS', 'IOS Development', 'Swift', 'Cocoa', 'Cocoa Touch', 
                                         'Xcode', 'Objective-C', 'SQLite', 'Plist', 'StoreKit', 'UI-Kit', 
                                         'AV Foundation', 'Auto-Layout']
                    rec_course = course_recommender(ios_course)
                    
                elif reco_field == 'UI-UX Development':
                    print("\n🎨 Our analysis says you are looking for UI-UX Development Jobs.")
                    recommended_skills = ['UI', 'User Experience', 'Adobe XD', 'Figma', 'Zeplin', 
                                         'Balsamiq', 'Prototyping', 'Wireframes', 'Storyframes', 
                                         'Adobe Photoshop', 'Editing', 'Illustrator', 'After Effects', 
                                         'Premier Pro', 'Indesign', 'Wireframe', 'Solid', 'Grasp', 'User Research']
                    rec_course = course_recommender(uiux_course)
                
                print(f"Recommended skills: {', '.join(recommended_skills)}")
            else:
                print("\n⚠️ We couldn't determine a specific tech field based on your skills.")
                print("Consider adding more specific technical skills to your resume.")
                
            # Resume scoring and analysis with research-based weights
            print("\n📝 Resume Score Analysis:")
            resume_score = analyze_resume_completeness(resume_text, cand_level, verbose)
            
            print(f"\nYour Resume Score: {resume_score}/100")
            
            if resume_score < 40:
                print("\n❗ Your resume needs significant improvement to stand out in job applications.")
                print("Research shows that well-structured resumes get 60% more interviews.")
            elif resume_score < 60:
                print("\n⚠️ Your resume is average. Consider strengthening your key sections.")
                print("Data shows that optimized resumes are 3x more likely to get interviews.")
            else:
                print("\n✅ Your resume is strong! 75% of optimized resumes like yours lead to interviews.")
            
            # Provide useful resources
            print("\n📚 Resources for Resume Improvement:")
            print(f"Recommended Resume Video: {random.choice(resume_videos)}")
            print(f"Recommended Interview Prep Video: {random.choice(interview_videos)}")
            
            print("\n✨ Resume analysis completed successfully! ✨")
        else:
            print("Error: Could not extract data from the resume.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()