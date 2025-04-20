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
    Extract name from resume text using multiple heuristics
    """
    # Common resume header patterns that often contain names
    name_patterns = [
        r'(?i)^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',  # First line capitalized names
        r'(?i)Name\s*:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',  # Name: format
        r'(?i)([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s*\n.*?[0-9]',  # Name followed by contact info
    ]
    
    # Try each pattern
    for pattern in name_patterns:
        matches = re.search(pattern, resume_text)
        if matches:
            return matches.group(1).strip()
    
    # Fall back to first line if all else fails
    first_line = resume_text.strip().split('\n')[0].strip()
    if len(first_line.split()) <= 4 and not '@' in first_line and not re.search(r'\d', first_line):
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

# Analyze how comprehensive the resume is
def analyze_resume_completeness(resume_text, verbose=False):
    """
    Check for various sections in the resume and score accordingly
    """
    resume_score = 0
    results = []
    
    # Check for various sections in the resume with improved section detection
    score_checks = [
        ('Objective', ['Objective', 'Summary', 'Career Objective', 'Professional Summary'], 6, 
         "You have added Objective/Summary", "Consider adding a career objective to clarify your intentions."),
        
        ('Education', ['Education', 'School', 'College', 'University', 'Bachelor', 'Master', 'Ph.D', 'B.Tech', 'M.Tech'], 12, 
         "You have added Education Details", "Add education details to showcase your qualifications."),
        
        ('Experience', ['Experience', 'Work Experience', 'Professional Experience', 'Employment History'], 16, 
         "You have added Experience", "Add experience to stand out from the crowd."),
        
        ('Internship', ['Internship', 'Internships'], 6, 
         "You have added Internships", "Add internships to enhance your profile."),
        
        ('Skills', ['Skills', 'Technical Skills', 'Core Competencies', 'Key Skills'], 7, 
         "You have added Skills", "Add skills to better showcase your abilities."),
        
        ('Hobbies', ['Hobbies', 'Interests', 'Activities'], 4, 
         "You have added your Hobbies", "Add hobbies to show your personality."),
        
        ('Achievements', ['Achievements', 'Awards', 'Honors', 'Recognition'], 13, 
         "You have added your Achievements", "Add achievements to demonstrate your capabilities."),
        
        ('Certifications', ['Certifications', 'Certification', 'Professional Certifications'], 12, 
         "You have added your Certifications", "Add certifications to showcase your specializations."),
        
        ('Projects', ['Projects', 'Project', 'Academic Projects', 'Personal Projects'], 19, 
         "You have added your Projects", "Add projects to demonstrate practical experience.")
    ]
    
    for section_name, keywords, points, success_msg, missing_msg in score_checks:
        found = False
        for keyword in keywords:
            # Case insensitive search for both uppercase and non-uppercase variations
            if re.search(r'(?i)\b' + re.escape(keyword) + r'\b', resume_text):
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
            print("[-] Your resume is too short. Consider adding more content.")
        elif words > 700:
            print("[!] Your resume is quite long. Consider making it more concise.")
        
        # Check for contact information
        if not re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', resume_text):
            print("[-] No email found. Add your email address.")
        
        if not re.search(r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume_text):
            print("[-] No phone number found. Add your contact number.")
    
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
            # Determine candidate level
            cand_level = ''
            if resume_data['no_of_pages'] < 1:
                cand_level = "NA"
                print("\nYou are at Fresher level!")
            elif re.search(r'(?i)internship', resume_text):
                cand_level = "Intermediate"
                print("\nYou are at Intermediate level!")
            elif re.search(r'(?i)experience|work experience', resume_text):
                cand_level = "Experienced"
                print("\nYou are at Experienced level!")
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
                
            # Resume scoring and analysis
            print("\n📝 Resume Score Analysis:")
            resume_score = analyze_resume_completeness(resume_text, verbose)
            
            print(f"\nYour Resume Score: {resume_score}/100")
            
            if resume_score < 40:
                print("\n❗ Your resume needs significant improvement to stand out in job applications.")
            elif resume_score < 60:
                print("\n⚠️ Your resume is average. Consider adding more sections to make it stronger.")
            else:
                print("\n✅ Your resume is quite strong! Minor improvements could still be made.")
            
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