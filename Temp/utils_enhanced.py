# utils_enhanced.py - Enhanced resume parsing utilities
import re
import nltk
import spacy
from spacy.matcher import Matcher

# Download necessary NLTK data
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('maxent_ne_chunker', quiet=True)
nltk.download('words', quiet=True)

def extract_name_advanced(resume_text, nlp_doc=None, matcher=None):
    """
    Extract candidate name from resume text using multiple techniques
    
    Args:
        resume_text (str): The raw text extracted from resume
        nlp_doc (spacy.Doc, optional): Pre-processed spaCy document
        matcher (spacy.Matcher, optional): Initialized spaCy matcher
        
    Returns:
        str: Extracted name or "Name not found"
    """
    # Method 1: Parse the first few lines for name patterns
    name_candidates = []
    
    # Get first 10 lines for header analysis
    first_lines = resume_text.strip().split('\n')[:10]
    header_text = '\n'.join(first_lines)
    
    # Common resume header patterns
    name_patterns = [
        # Name at the beginning with 2-3 capitalized words
        r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s*$',
        
        # Name with professional designations
        r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})(?:\s*,\s*[A-Za-z. ]+)?$',
        
        # Name followed by contact info
        r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s*\n',
        
        # Name in "Name: John Doe" format
        r'(?i)Name\s*:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
        
        # Name in "Name - John Doe" format
        r'(?i)Name\s*-\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
    ]
    
    # Try each pattern on the header
    for pattern in name_patterns:
        matches = re.search(pattern, header_text, re.MULTILINE)
        if matches:
            name_candidates.append(matches.group(1).strip())
    
    # Method 2: Use NLTK Named Entity Recognition
    try:
        tokens = nltk.tokenize.word_tokenize(header_text)
        pos_tags = nltk.pos_tag(tokens)
        ne_chunks = nltk.ne_chunk(pos_tags)
        
        # Extract named entities labeled as PERSON
        person_names = []
        current_name = []
        
        for chunk in ne_chunks:
            if isinstance(chunk, nltk.tree.Tree) and chunk.label() == 'PERSON':
                name_parts = [token for token, pos in chunk.leaves()]
                person_name = ' '.join(name_parts)
                person_names.append(person_name)
        
        if person_names:
            # Prefer longer names (more likely to be full names)
            person_names.sort(key=len, reverse=True)
            name_candidates.append(person_names[0])
    except Exception:
        pass
        
    # Method 3: Use spaCy NER if document is provided
    if nlp_doc:
        person_entities = [ent.text for ent in nlp_doc.ents if ent.label_ == 'PERSON']
        if person_entities:
            # Prefer entities near the beginning of the document
            for entity in person_entities[:3]:
                name_candidates.append(entity)
    
    # Method 4: Use custom spaCy patterns if matcher is provided
    if matcher and nlp_doc:
        # Pattern for typical name formats (2-3 capitalized words)
        name_pattern = [
            [{"SHAPE": "Xxx"}, {"SHAPE": "Xxx"}],  # First Last
            [{"SHAPE": "Xxx"}, {"SHAPE": "Xxx"}, {"SHAPE": "Xxx"}],  # First Middle Last
            [{"SHAPE": "Xxx"}, {"TEXT": "."}, {"SHAPE": "Xxx"}],  # First Initial Last
        ]
        
        for pattern in name_pattern:
            matcher.add("NAME_PATTERN", [pattern])
        
        matches = matcher(nlp_doc)
        
        for match_id, start, end in matches:
            span = nlp_doc[start:end]
            # Only consider matches that appear early in the document
            if span.start < 100:  # Within first 100 tokens
                name_candidates.append(span.text)
    
    # Filter and validate candidates
    valid_names = []
    for name in name_candidates:
        # Basic validation
        if name and len(name.split()) >= 2:
            # Skip if contains common non-name indicators
            skip_indicators = ['resume', 'cv', 'curriculum', 'vitae', 'address', 'email', 
                              'phone', 'tel', 'contact', '@', 'www', 'http']
            
            if not any(indicator in name.lower() for indicator in skip_indicators):
                valid_names.append(name)
    
    # Return the most likely name based on position and validation
    if valid_names:
        # If we have multiple valid candidates, prefer the first ones
        # as they're likely from the header
        return valid_names[0]
    
    # Last resort: first non-empty, reasonably-sized line that might be a name
    for line in first_lines:
        line = line.strip()
        if line and len(line.split()) <= 4 and not any(c.isdigit() for c in line) and '@' not in line:
            return line
            
    return "Name not found"

def validate_extracted_data(data):
    """
    Validate and clean extracted resume data
    
    Args:
        data (dict): Dictionary of extracted resume data
        
    Returns:
        dict: Validated and cleaned data
    """
    validated = data.copy()
    
    # Validate name
    if validated.get('name'):
        name = validated['name']
        # Remove unwanted prefixes/suffixes
        name_prefixes = ['name:', 'name', 'full name:', 'full name']
        for prefix in name_prefixes:
            if name.lower().startswith(prefix):
                name = name[len(prefix):].strip()
        
        # Remove common suffixes
        name_suffixes = [', ph.d', ', mba', ', m.s.', ', b.s.', ', b.a.']
        for suffix in name_suffixes:
            if name.lower().endswith(suffix):
                name = name[:-(len(suffix))].strip()
                
        validated['name'] = name
    
    # Validate skills - remove duplicates and normalize
    if validated.get('skills'):
        # Convert to set to remove duplicates, then back to list
        unique_skills = list(set([skill.strip() for skill in validated['skills']]))
        validated['skills'] = unique_skills
    
    return validated

def combine_extraction_methods(resume_text, nlp_doc=None):
    """
    Combine multiple extraction methods for better results
    
    Args:
        resume_text (str): The raw text extracted from resume
        nlp_doc (spacy.Doc, optional): Pre-processed spaCy document
        
    Returns:
        dict: Extracted data with higher confidence
    """
    results = {}
    
    # Create matcher
    nlp = spacy.load('en_core_web_sm') if not nlp_doc else nlp_doc.vocab.strings
    matcher = Matcher(nlp.vocab if hasattr(nlp, 'vocab') else nlp)
    
    # Extract name using enhanced method
    results['name'] = extract_name_advanced(resume_text, nlp_doc, matcher)
    
    # Other extractions would go here...
    
    return validate_extracted_data(results)