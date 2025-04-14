#!/usr/bin/env python3
import argparse
import base64
import os
import time
import datetime
import socket
import platform
import geocoder
import secrets
import random
import psycopg2
from psycopg2 import sql
from pyresparser import ResumeParser
from pdfminer3.layout import LAParams, LTTextBox
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager
from pdfminer3.pdfinterp import PDFPageInterpreter
from pdfminer3.converter import TextConverter
import io 
from geopy.geocoders import Nominatim
from Courses import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos
import nltk
import sys

# Download nltk stopwords if needed
nltk.download('stopwords', quiet=True)

# Parse command line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description='Resume Parser with PostgreSQL')
    parser.add_argument('pdf_path', help='Path to the resume PDF file')
    parser.add_argument('--name', required=True, help='Your name')
    parser.add_argument('--email', required=True, help='Your email')
    parser.add_argument('--mobile', required=True, help='Your mobile number')
    return parser.parse_args()

# Connect to PostgreSQL database
def connect_to_db():
    try:
        conn = psycopg2.connect(
            dbname="cv",
            user="postgres",
            password="root",
            host="localhost",
            port="5432"
        )
        print("Connected to PostgreSQL successfully!")
        return conn
    except Exception as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        sys.exit(1)

# Create necessary tables if they don't exist
def create_tables(conn):
    cursor = conn.cursor()
    
    # Create user_data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_data (
            ID SERIAL PRIMARY KEY,
            sec_token VARCHAR(20) NOT NULL,
            ip_add VARCHAR(50),
            host_name VARCHAR(50),
            dev_user VARCHAR(50),
            os_name_ver VARCHAR(50),
            latlong VARCHAR(50),
            city VARCHAR(50),
            state VARCHAR(50),
            country VARCHAR(50),
            act_name VARCHAR(50) NOT NULL,
            act_mail VARCHAR(50) NOT NULL,
            act_mob VARCHAR(20) NOT NULL,
            name VARCHAR(500) NOT NULL,
            email VARCHAR(500) NOT NULL,
            resume_score VARCHAR(8) NOT NULL,
            timestamp VARCHAR(50) NOT NULL,
            page_no VARCHAR(5) NOT NULL,
            predicted_field TEXT NOT NULL,
            user_level TEXT NOT NULL,
            actual_skills TEXT NOT NULL,
            recommended_skills TEXT NOT NULL,
            recommended_courses TEXT NOT NULL,
            pdf_name VARCHAR(50) NOT NULL
        )
    ''')
    
    # Create feedback table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_feedback (
            ID SERIAL PRIMARY KEY,
            feed_name VARCHAR(50) NOT NULL,
            feed_email VARCHAR(50) NOT NULL,
            feed_score VARCHAR(5) NOT NULL,
            comments VARCHAR(100),
            timestamp VARCHAR(50) NOT NULL
        )
    ''')
    
    conn.commit()
    print("Database tables created successfully!")

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

# Insert resume data into the database
def insert_data(conn, sec_token, ip_add, host_name, dev_user, os_name_ver, latlong, city, state, country, 
                act_name, act_mail, act_mob, name, email, res_score, timestamp, no_of_pages, 
                reco_field, cand_level, skills, recommended_skills, courses, pdf_name):
    
    cursor = conn.cursor()
    
    insert_sql = '''
        INSERT INTO user_data 
        (sec_token, ip_add, host_name, dev_user, os_name_ver, latlong, city, state, country, 
         act_name, act_mail, act_mob, name, email, resume_score, timestamp, page_no, 
         predicted_field, user_level, actual_skills, recommended_skills, recommended_courses, pdf_name)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    '''
    
    rec_values = (str(sec_token), str(ip_add), host_name, dev_user, os_name_ver, str(latlong), 
                  city, state, country, act_name, act_mail, act_mob, name, email, 
                  str(res_score), timestamp, str(no_of_pages), reco_field, cand_level, 
                  str(skills), str(recommended_skills), str(courses), pdf_name)
    
    cursor.execute(insert_sql, rec_values)
    conn.commit()
    print("Resume data inserted into database successfully!")

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

# Main function
def main():
    args = parse_arguments()
    pdf_path = args.pdf_path
    pdf_name = os.path.basename(pdf_path)
    act_name = args.name
    act_mail = args.email
    act_mob = args.mobile
    
    # Check if the PDF file exists
    if not os.path.exists(pdf_path):
        print(f"Error: The file {pdf_path} does not exist.")
        sys.exit(1)
    
    # Connect to PostgreSQL and create tables
    conn = connect_to_db()
    create_tables(conn)
    
    print(f"\nProcessing resume: {pdf_name}\n")
    
    # Collect system information
    sec_token = secrets.token_urlsafe(12)
    host_name = socket.gethostname()
    ip_add = socket.gethostbyname(host_name)
    dev_user = os.getlogin()
    os_name_ver = platform.system() + " " + platform.release()
    
    # Collect geographic information
    try:
        g = geocoder.ip('me')
        latlong = g.latlng
        geolocator = Nominatim(user_agent="resume_parser")
        location = geolocator.reverse(latlong, language='en')
        address = location.raw['address']
        city = address.get('city', '')
        state = address.get('state', '')
        country = address.get('country', '')
    except Exception as e:
        print(f"Warning: Could not get geolocation info: {e}")
        latlong = None
        city = state = country = ''
    
    # Parse the resume
    print("Analyzing your resume...")
    resume_data = ResumeParser(pdf_path).get_extracted_data()
    
    if resume_data:
        # Get the whole resume text
        resume_text = pdf_reader(pdf_path)
        
        # Basic info
        print("\n📄 Basic Information:")
        print(f"Name: {resume_data.get('name', 'Not found')}")
        print(f"Email: {resume_data.get('email', 'Not found')}")
        print(f"Contact: {resume_data.get('mobile_number', 'Not found')}")
        print(f"Degree: {resume_data.get('degree', 'Not found')}")
        print(f"Resume pages: {resume_data.get('no_of_pages', 'Not found')}")
        
        # Determine candidate level
        cand_level = ''
        if resume_data['no_of_pages'] < 1:
            cand_level = "NA"
            print("\nYou are at Fresher level!")
        elif any(keyword in resume_text for keyword in ['INTERNSHIP', 'INTERNSHIPS', 'Internship', 'Internships']):
            cand_level = "Intermediate"
            print("\nYou are at Intermediate level!")
        elif any(keyword in resume_text for keyword in ['EXPERIENCE', 'WORK EXPERIENCE', 'Experience', 'Work Experience']):
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
        ds_keyword = ['tensorflow', 'keras', 'pytorch', 'machine learning', 'deep Learning', 'flask', 'streamlit']
        web_keyword = ['react', 'django', 'node jS', 'react js', 'php', 'laravel', 'magento', 'wordpress', 'javascript', 'angular js', 'C#', 'Asp.net', 'flask']
        android_keyword = ['android', 'android development', 'flutter', 'kotlin', 'xml', 'kivy']
        ios_keyword = ['ios', 'ios development', 'swift', 'cocoa', 'cocoa touch', 'xcode']
        uiux_keyword = ['ux', 'adobe xd', 'figma', 'zeplin', 'balsamiq', 'ui', 'prototyping', 'wireframes', 'storyframes', 'adobe photoshop', 'photoshop', 'editing', 'adobe illustrator', 'illustrator', 'adobe after effects', 'after effects', 'adobe premier pro', 'premier pro', 'adobe indesign', 'indesign', 'wireframe', 'solid', 'grasp', 'user research', 'user experience']
        n_any = ['english', 'communication', 'writing', 'microsoft office', 'leadership', 'customer management', 'social media']
        
        # Predict field and recommend skills
        recommended_skills = []
        reco_field = ''
        rec_course = ''
        
        # Check skills to predict field
        for skill in skills:
            skill_lower = skill.lower()
            
            # Data science field
            if skill_lower in ds_keyword:
                reco_field = 'Data Science'
                print("\n📊 Our analysis says you are looking for Data Science Jobs.")
                recommended_skills = ['Data Visualization', 'Predictive Analysis', 'Statistical Modeling', 'Data Mining', 
                                     'Clustering & Classification', 'Data Analytics', 'Quantitative Analysis', 
                                     'Web Scraping', 'ML Algorithms', 'Keras', 'Pytorch', 'Probability', 
                                     'Scikit-learn', 'Tensorflow', 'Flask', 'Streamlit']
                print(f"Recommended skills: {', '.join(recommended_skills)}")
                rec_course = course_recommender(ds_course)
                break
                
            # Web development field
            elif skill_lower in web_keyword:
                reco_field = 'Web Development'
                print("\n🌐 Our analysis says you are looking for Web Development Jobs.")
                recommended_skills = ['React', 'Django', 'Node JS', 'React JS', 'php', 'laravel', 'Magento', 
                                     'wordpress', 'Javascript', 'Angular JS', 'c#', 'Flask', 'SDK']
                print(f"Recommended skills: {', '.join(recommended_skills)}")
                rec_course = course_recommender(web_course)
                break
                
            # Android development field
            elif skill_lower in android_keyword:
                reco_field = 'Android Development'
                print("\n📱 Our analysis says you are looking for Android App Development Jobs.")
                recommended_skills = ['Android', 'Android development', 'Flutter', 'Kotlin', 'XML', 
                                     'Java', 'Kivy', 'GIT', 'SDK', 'SQLite']
                print(f"Recommended skills: {', '.join(recommended_skills)}")
                rec_course = course_recommender(android_course)
                break
                
            # iOS development field
            elif skill_lower in ios_keyword:
                reco_field = 'IOS Development'
                print("\n📱 Our analysis says you are looking for IOS App Development Jobs.")
                recommended_skills = ['IOS', 'IOS Development', 'Swift', 'Cocoa', 'Cocoa Touch', 
                                     'Xcode', 'Objective-C', 'SQLite', 'Plist', 'StoreKit', 'UI-Kit', 
                                     'AV Foundation', 'Auto-Layout']
                print(f"Recommended skills: {', '.join(recommended_skills)}")
                rec_course = course_recommender(ios_course)
                break
                
            # UI-UX development field
            elif skill_lower in uiux_keyword:
                reco_field = 'UI-UX Development'
                print("\n🎨 Our analysis says you are looking for UI-UX Development Jobs.")
                recommended_skills = ['UI', 'User Experience', 'Adobe XD', 'Figma', 'Zeplin', 
                                     'Balsamiq', 'Prototyping', 'Wireframes', 'Storyframes', 
                                     'Adobe Photoshop', 'Editing', 'Illustrator', 'After Effects', 
                                     'Premier Pro', 'Indesign', 'Wireframe', 'Solid', 'Grasp', 'User Research']
                print(f"Recommended skills: {', '.join(recommended_skills)}")
                rec_course = course_recommender(uiux_course)
                break
                
            # Not available field
            elif skill_lower in n_any:
                reco_field = 'NA'
                print("\n⚠️ Currently our tool only predicts and recommends for Data Science, Web, Android, IOS and UI/UX Development")
                recommended_skills = ['No Recommendations']
                rec_course = "Sorry! Not Available for this Field"
                break
        
        # If no prediction made from the loop, set a default
        if not reco_field:
            reco_field = 'Other'
            print("\nBased on your skills, we couldn't determine a specific tech field.")
            recommended_skills = ['Consider adding more technical skills to your resume']
        
        # Resume scoring
        print("\n📝 Resume Score Analysis:")
        resume_score = 0
        
        # Check for various sections in the resume
        score_checks = [
            ('Objective', ['Objective', 'Summary'], 6, "You have added Objective/Summary"),
            ('Education', ['Education', 'School', 'College'], 12, "You have added Education Details"),
            ('Experience', ['EXPERIENCE', 'Experience'], 16, "You have added Experience"),
            ('Internship', ['INTERNSHIPS', 'INTERNSHIP', 'Internships', 'Internship'], 6, "You have added Internships"),
            ('Skills', ['SKILLS', 'SKILL', 'Skills', 'Skill'], 7, "You have added Skills"),
            ('Hobbies', ['HOBBIES', 'Hobbies'], 4, "You have added your Hobbies"),
            ('Interests', ['INTERESTS', 'Interests'], 5, "You have added your Interest"),
            ('Achievements', ['ACHIEVEMENTS', 'Achievements'], 13, "You have added your Achievements"),
            ('Certifications', ['CERTIFICATIONS', 'Certifications', 'Certification'], 12, "You have added your Certifications"),
            ('Projects', ['PROJECTS', 'PROJECT', 'Projects', 'Project'], 19, "You have added your Projects")
        ]
        
        for section_name, keywords, points, success_msg in score_checks:
            if any(keyword in resume_text for keyword in keywords):
                resume_score += points
                print(f"[+] {success_msg} (+{points} points)")
            else:
                missing_msg = {
                    'Objective': "Consider adding a career objective to clarify your intentions.",
                    'Education': "Add education details to showcase your qualifications.",
                    'Experience': "Add experience to stand out from the crowd.",
                    'Internship': "Add internships to enhance your profile.",
                    'Skills': "Add skills to better showcase your abilities.",
                    'Hobbies': "Add hobbies to show your personality.",
                    'Interests': "Add interests to show what you care about outside work.",
                    'Achievements': "Add achievements to demonstrate your capabilities.",
                    'Certifications': "Add certifications to showcase your specializations.",
                    'Projects': "Add projects to demonstrate practical experience."
                }
                print(f"[-] {missing_msg.get(section_name, 'Consider adding this section.')}")
        
        print(f"\nYour Resume Score: {resume_score}/100")
        
        # Get current timestamp
        ts = time.time()
        cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
        timestamp = str(cur_date + '_' + cur_time)
        
        # Insert data into PostgreSQL
        insert_data(
            conn, sec_token, ip_add, host_name, dev_user, os_name_ver, latlong, city, state, country,
            act_name, act_mail, act_mob, resume_data['name'], resume_data['email'], str(resume_score),
            timestamp, str(resume_data['no_of_pages']), reco_field, cand_level, str(resume_data['skills']),
            str(recommended_skills), str(rec_course), pdf_name
        )
        
        # Provide useful resources
        print("\n📚 Resources for Resume Improvement:")
        print(f"Recommended Resume Video: {random.choice(resume_videos)}")
        print(f"Recommended Interview Prep Video: {random.choice(interview_videos)}")
        
        print("\n✨ Resume analysis completed successfully! ✨")
    else:
        print("Error: Could not extract data from the resume.")
    
    # Close the database connection
    conn.close()

if __name__ == "__main__":
    main()