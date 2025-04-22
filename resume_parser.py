# resume_parser.py - Enhanced version
import os
import multiprocessing as mp
import io
import spacy
import pprint
from spacy.matcher import Matcher
from . import utils
from . import utils_enhanced  # Import our new utilities

class ResumeParser(object):

    def __init__(
        self,
        resume,
        skills_file=None,
        custom_regex=None
    ):
        nlp = spacy.load('en_core_web_sm')
        custom_nlp = spacy.load(os.path.dirname(os.path.abspath(__file__)))
        self.__skills_file = skills_file
        self.__custom_regex = custom_regex
        self.__matcher = Matcher(nlp.vocab)
        self.__details = {
            'name': None,
            'email': None,
            'mobile_number': None,
            'skills': None,
            'degree': None,
            'no_of_pages': None,
        }
        self.__resume = resume
        if not isinstance(self.__resume, io.BytesIO):
            ext = os.path.splitext(self.__resume)[1].split('.')[1]
        else:
            ext = self.__resume.name.split('.')[1]
        self.__text_raw = utils.extract_text(self.__resume, '.' + ext)
        self.__text = ' '.join(self.__text_raw.split())
        self.__nlp = nlp(self.__text)
        self.__custom_nlp = custom_nlp(self.__text_raw)
        self.__noun_chunks = list(self.__nlp.noun_chunks)
        self.__get_basic_details()

    def get_extracted_data(self):
        # Add confidence scores to the output
        validated_details = utils_enhanced.validate_extracted_data(self.__details)
        return validated_details

    def __get_basic_details(self):
        cust_ent = utils.extract_entities_wih_custom_model(
                            self.__custom_nlp
                        )
        # Use our enhanced name extraction as primary method
        name_advanced = utils_enhanced.extract_name_advanced(
            self.__text_raw, 
            self.__nlp,
            self.__matcher
        )
        
        # Traditional methods as backup
        name = utils.extract_name(self.__nlp, matcher=self.__matcher)
        email = utils.extract_email(self.__text)
        mobile = utils.extract_mobile_number(self.__text, self.__custom_regex)
        skills = utils.extract_skills(
                    self.__nlp,
                    self.__noun_chunks,
                    self.__skills_file
                )

        entities = utils.extract_entity_sections_grad(self.__text_raw)

        # extract name with improved priority order
        if name_advanced != "Name not found":
            self.__details['name'] = name_advanced
        elif 'Name' in cust_ent and cust_ent['Name']:
            self.__details['name'] = cust_ent['Name'][0]
        else:
            self.__details['name'] = name

        # extract email
        self.__details['email'] = email

        # extract mobile number
        self.__details['mobile_number'] = mobile

        # extract skills
        self.__details['skills'] = skills

        # no of pages
        self.__details['no_of_pages'] = utils.get_number_of_pages(self.__resume)

        # extract education Degree
        try:
            self.__details['degree'] = cust_ent['Degree']
        except KeyError:
            pass

        return