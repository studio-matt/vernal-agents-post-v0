from pydantic import BaseModel
from typing import List, Optional, Dict
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer, PorterStemmer
from nltk.corpus import stopwords
from nltk import pos_tag, ne_chunk
# Gensim is optional - only needed for system model topic extraction
try:
    import gensim
    from gensim import corpora, models
    GENSIM_AVAILABLE_TOP_LEVEL = True
except ImportError:
    gensim = None
    corpora = None
    models = None
    GENSIM_AVAILABLE_TOP_LEVEL = False
    logger.warning("⚠️ Gensim not available at module level - system model topic extraction will not work")
from collections import Counter
import numpy as np
import logging
import os
import json

# Cache for topic extraction prompt (loaded from database)
_topic_prompt_cache = None
_topic_prompt_cache_time = None

# Set up logging first
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# langchain_openai is optional - only needed for LLM model
try:
    from langchain_openai import ChatOpenAI
    LANGCHAIN_OPENAI_AVAILABLE = True
except ImportError:
    ChatOpenAI = None
    LANGCHAIN_OPENAI_AVAILABLE = False
    logger.warning("⚠️ langchain_openai not available - LLM model will not work")

# sklearn is optional - only needed for NMF and LSA models
try:
    from sklearn.decomposition import NMF, TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    NMF = None
    TruncatedSVD = None
    TfidfVectorizer = None
    SKLEARN_AVAILABLE = False
    logger.warning("⚠️ sklearn not available - NMF and LSA models will not work")

# BERTopic is optional - only needed for bertopic_model function
try:
    from bertopic import BERTopic
    BERTOPIC_AVAILABLE = True
except ImportError:
    BERTopic = None
    BERTOPIC_AVAILABLE = False
    logger.warning("⚠️ BERTopic not available - bertopic_model function will not work")

# Ensure NLTK resources are downloaded
try:
    nltk.data.find('corpora/stopwords')
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/wordnet')
    nltk.data.find('chunkers/maxent_ne_chunker')
    nltk.data.find('corpora/words')
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('maxent_ne_chunker', quiet=True)
    nltk.download('words', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)

lemmatizer = WordNetLemmatizer()
stemmer = PorterStemmer()
# Domain-specific stop words
additional_stopwords = ['tools', 'tasks', 'include', 'agents', 'like', 'roles', 'http', 'https', 'www', 'crewai', 'defined', 'agent', 'web', 'content', 'various', 'engaging', 'existing']
stop_words = set(stopwords.words('english')) | set(additional_stopwords)

class Post(BaseModel):
    text: str

class Posts(BaseModel):
    posts: List[Post]

class ProcessedPost(BaseModel):
    text: str
    lemmatized_text: Optional[str] = None
    stemmed_text: Optional[str] = None
    stopwords_removed_text: Optional[str] = None
    persons: Optional[List[str]] = None
    organizations: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    dates: Optional[List[str]] = None
    topics: Optional[List[str]] = None

class ProcessedPosts(BaseModel):
    posts: List[ProcessedPost]

def lemmatize_text(text: str) -> str:
    words = word_tokenize(text)
    lemmatized_words = [lemmatizer.lemmatize(word) for word in words]
    return ' '.join(lemmatized_words)

def stem_text(text: str) -> str:
    words = word_tokenize(text)
    stemmed_words = [stemmer.stem(word) for word in words]
    return ' '.join(stemmed_words)

def clear_topic_prompt_cache():
    """Clear the cached topic extraction prompt (call after updating in DB)"""
    global _topic_prompt_cache, _topic_prompt_cache_time
    _topic_prompt_cache = None
    _topic_prompt_cache_time = None
    logger.info("✅ Cleared topic extraction prompt cache")

def get_topic_extraction_prompt() -> str:
    """
    Get the topic extraction prompt from database, with fallback to default.
    Caches the prompt for 5 minutes to reduce database queries.
    """
    global _topic_prompt_cache, _topic_prompt_cache_time
    
    import time
    
    # Check cache (5 minute TTL)
    if _topic_prompt_cache and _topic_prompt_cache_time:
        if time.time() - _topic_prompt_cache_time < 300:  # 5 minutes
            return _topic_prompt_cache
    
    # Default prompt (fallback)
    default_prompt = """You are an expert in topic modeling. Your task is to review the scraped information and extract a list of salient topic names as short, descriptive phrases.

CRITICAL REQUIREMENTS:
- Each topic MUST be a short, descriptive phrase (2-4 words) that captures a distinct concept
- Each topic name should be a multi-word phrase if that improves clarity
- Examples of good topics: 'football offense', 'public health policy', 'gun violence', 'vietnam war history', 'military strategy analysis'
- NEVER return single words (e.g., "war", "vietnam", "football", "health" are INVALID)
- Each phrase must be meaningful, descriptive, and stand alone as an important theme
- Phrases should reflect specific concepts found in the scraped content, not vague terms
- Ensure topics are distinct and capture different aspects of the content
- Prioritize topics that are most relevant to the scraped texts, query, keywords, and URLs

STRICTLY FORBIDDEN - DO NOT EXTRACT:
- UI instructions or commands (e.g., "press ctrl", "place your cursor", "enter number", "duplicate pages")
- Software interface elements (e.g., "blank page", "page break", "min read", "want to duplicate")
- Keyboard shortcuts or commands (e.g., "press ctrl +", "windows or command")
- Tutorial step instructions (e.g., "how to duplicate", "select all", "copy paste")
- Technical identifiers or file extensions (e.g., "press.isbn", "document.pdf", URLs)
- Generic action phrases without context (e.g., "open file", "save document", "close window")

Focus on EXTRACTING THEMES AND CONCEPTS, not the instructions for how to use software.

Return EXACTLY {num_topics} topics as a JSON array of strings. Each string must be a 2-4 word descriptive phrase. Do not include explanations, additional text, or markdown formatting (e.g., ```json), just the JSON array.

Example VALID output:
["vietnam war history", "military strategy analysis", "cold war politics", "southeast asia conflict", "combat operations planning"]

Example INVALID output (DO NOT DO THIS):
["war", "vietnam", "history", "military", "strategy"]  ← These are single words, NOT valid
["press ctrl", "place cursor", "duplicate pages", "blank page"]  ← These are UI instructions, NOT valid topics

Context:
{context}"""
    
    # Try to load from database
    try:
        from database import SessionLocal
        db = SessionLocal()
        try:
            from models import SystemSettings
            setting = db.query(SystemSettings).filter(
                SystemSettings.setting_key == "topic_extraction_prompt"
            ).first()
            
            if setting and setting.setting_value:
                # Update cache
                _topic_prompt_cache = setting.setting_value
                _topic_prompt_cache_time = time.time()
                logger.info("✅ Loaded topic extraction prompt from database")
                return setting.setting_value
            else:
                logger.warning("⚠️ Topic extraction prompt not found in database, using default")
        except Exception as db_err:
            logger.warning(f"⚠️ Failed to load prompt from database: {db_err}, using default")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"⚠️ Database not available for prompt loading: {e}, using default")
    
    # Return default and cache it
    _topic_prompt_cache = default_prompt
    _topic_prompt_cache_time = time.time()
    return default_prompt

def remove_stopwords(text: str) -> str:
    words = word_tokenize(text)
    filtered_words = [word for word in words if word.lower() not in stop_words]
    return ' '.join(filtered_words)

def extract_entities(text: str, extract_persons: bool, extract_organizations: bool, extract_locations: bool, extract_dates: bool, 
                     extract_money: bool = False, extract_percent: bool = False, extract_time: bool = False, extract_facility: bool = False) -> Dict[str, List[str]]:
    import re
    entities = {
        'persons': [],
        'organizations': [],
        'locations': [],
        'dates': [],
        'money': [],
        'percent': [],
        'time': [],
        'facility': []
    }
    if not any([extract_persons, extract_organizations, extract_locations, extract_dates, extract_money, extract_percent, extract_time, extract_facility]):
        return entities

    # Extract NLTK entities (PERSON, ORGANIZATION, GPE, DATE)
    try:
        words = word_tokenize(text)
        pos_tags = pos_tag(words)
        # Use binary=False to get detailed entity types (PERSON, ORGANIZATION, GPE, etc.)
        chunks = ne_chunk(pos_tags, binary=False)
    except Exception as e:
        logger.warning(f"NLTK entity extraction failed: {e}, using regex fallback only")
        chunks = []

    for chunk in chunks:
        if hasattr(chunk, 'label'):
            entity_type = chunk.label()
            entity_text = ' '.join(c[0] for c in chunk)
            if entity_type == 'PERSON' and extract_persons:
                # Filter out software names, UI elements, and product names
                entity_lower = entity_text.lower()
                entity_words = entity_text.split()
                
                software_ui_indicators = [
                    'microsoft', 'word', 'excel', 'powerpoint', 'outlook', 'windows', 'macintosh', 'apple', 'mac',
                    'google', 'chrome', 'firefox', 'safari', 'edge', 'internet', 'explorer', 'browser',
                    'edit', 'view', 'file', 'insert', 'format', 'tools', 'table', 'help', 'developer',
                    'initial', 'predecessor', 'multi', 'type', 'license', 'trialware', 'website', 'tool',
                    'share', 'print', 'save', 'open', 'close', 'new', 'copy', 'paste', 'cut',
                    'office', 'media', 'unix', 'independent', 'wikimedia', 'foundation', 'project', 'wikipedia',
                    'regular', 'guys', 'built', 'wordperfect', 'eclectic', 'light', 'digital', 'writing'
                ]
                
                # Additional validation: Person names should be 2-4 words, both capitalized
                # Skip single words (too ambiguous)
                if len(entity_words) == 1:
                    continue
                
                # Skip if any word is a software/UI indicator
                if any(word.lower() in software_ui_indicators for word in entity_words):
                    continue
                
                # Skip if it's clearly software/UI (contains indicators)
                if any(indicator in entity_lower for indicator in software_ui_indicators):
                    continue
                
                # Skip if it's a common phrase pattern (not a name)
                common_phrases = [
                    'edit view', 'tool word', 'type word', 'license trialware', 'microsoft word', 'apple macintosh',
                    # UI instruction phrases
                    'to how', 'duplicate pages', 'page document if', 'press ctrl', 'blank page', 'page break',
                    'different document you', 'sub duplicate', 'enter number', 'place your cursor', 'want to duplicate',
                    'min read', 'page you want', 'select all', 'copy paste'
                ]
                if entity_lower in common_phrases:
                    continue
                
                # Additional check: skip if it contains instruction words that make it clearly not a name
                instruction_words = ['to', 'how', 'duplicate', 'page', 'pages', 'document', 'if', 'press', 'ctrl', 'blank',
                                   'break', 'different', 'you', 'sub', 'enter', 'number', 'place', 'your', 'cursor',
                                   'want', 'min', 'read', 'select', 'copy', 'paste', 'open', 'close', 'save', 'print']
                # If more than half the words are instruction words, it's probably not a name
                instruction_count = sum(1 for word in entity_words if word.lower() in instruction_words)
                if instruction_count > len(entity_words) * 0.5:
                    continue
                
                entities['persons'].append(entity_text)
            elif entity_type == 'ORGANIZATION' and extract_organizations:
                # Filter out invalid organization entries
                entity_lower = entity_text.lower()
                entity_words = entity_text.split()
                
                # Skip if it contains person names or locations incorrectly labeled as organizations
                invalid_org_indicators = [
                    'louisville', 'muhammad', 'ali',  # Person name + location
                    'regular guys built wordperfect',  # Phrase, not an organization
                    'the eclectic light',  # Publication name, may be valid but let's be strict
                ]
                # Skip if it contains person names
                if any(indicator in entity_lower for indicator in invalid_org_indicators):
                    continue
                
                # Skip if it's a single generic word like "Office", "Media", "Independent" (but allow "Microsoft", "Apple", etc.)
                if len(entity_words) == 1:
                    generic_words = ['office', 'media', 'independent', 'digital', 'writing', 'page', 'document', 'document', 'tool', 'website']
                    known_orgs = ['microsoft', 'apple', 'google', 'amazon', 'meta', 'facebook', 'twitter', 'linkedin', 'nvidia', 'intel', 'amd']
                    if entity_lower in generic_words and entity_lower not in known_orgs:
                        continue
                
                # Skip if it's a UI instruction phrase
                instruction_words = ['to', 'how', 'duplicate', 'page', 'pages', 'document', 'if', 'press', 'ctrl', 'blank',
                                   'break', 'different', 'you', 'sub', 'enter', 'number', 'place', 'your', 'cursor',
                                   'want', 'min', 'read', 'select', 'copy', 'paste', 'open', 'close', 'save', 'print']
                instruction_count = sum(1 for word in entity_words if word.lower() in instruction_words)
                if instruction_count > len(entity_words) * 0.5:
                    continue
                
                entities['organizations'].append(entity_text)
            # NLTK sometimes labels organizations as GPE, so check for organization indicators
            elif entity_type == 'GPE':
                # Check if it's likely an organization (contains org words)
                if extract_organizations:
                    org_indicators = ['Corp', 'Corporation', 'Inc', 'LLC', 'Ltd', 'Company', 'University', 'College', 'School', 'Hospital', 'Foundation', 'Institute', 'Organization', 'Association']
                    if any(indicator in entity_text for indicator in org_indicators):
                        entities['organizations'].append(entity_text)
                    elif extract_locations:
                        # If not an organization, it's a location
                        entities['locations'].append(entity_text)
                elif extract_locations:
                    entities['locations'].append(entity_text)
            elif entity_type == 'DATE' and extract_dates:
                entities['dates'].append(entity_text)
            # NLTK sometimes labels facilities as ORGANIZATION, but we'll use regex for better coverage
            elif entity_type == 'FACILITY' and extract_facility:
                entities['facility'].append(entity_text)
    
    # Enhanced organization extraction using regex (for organizations NLTK might miss)
    if extract_organizations:
        org_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Corp|Corporation|Inc|LLC|Ltd|Company|Co|Industries|International|Group|Systems|Technologies|Solutions)\b',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:University|College|School|Institute|Academy|Foundation|Association|Society|Organization|Agency|Department|Bureau)\b',
            r'\b(?:The\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Hospital|Clinic|Medical Center|Bank|Trust|Fund)\b',
        ]
        for pattern in org_patterns:
            org_matches = re.findall(pattern, text)
            for match in org_matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1]
                # Exclude common non-org words
                if match and match not in {'The', 'A', 'An', 'United', 'States'} and match not in entities['organizations']:
                    entities['organizations'].append(match)
    
    # Enhanced date extraction using regex (for dates NLTK might miss)
    # Only extract complete dates: Month + Year or Month + Day + Year
    if extract_dates:
        # Comprehensive date patterns - only complete dates (non-capturing groups to avoid fragments)
        date_patterns = [
            # Month Day, Year (e.g., "January 15, 2024", "Jan 15 2024")
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\b',
            # Month Year (e.g., "January 2024", "Jan 2024")
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b',
            # MM/DD/YYYY or DD-MM-YYYY (e.g., "01/15/2024", "15-01-2024")
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',
            # YYYY/MM/DD (e.g., "2024/01/15")
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',
            # Ordinal dates (e.g., "15th of January 2024", "the 15th of January 2024")
            r'\b(?:the\s+)?\d{1,2}(?:st|nd|rd|th)\s+(?:of\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b',
            # Years with context (e.g., "in 2024", "2024.", "(2024)")
            r'\b(?:in\s+|the\s+year\s+)?(19\d{2}|20\d{2})(?:\s|$|\.|,|;|\)|\])\b',
        ]
        
        # Extract all date matches
        all_date_matches = []
        for pattern in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match_obj in matches:
                full_match = match_obj.group(0).strip('.,;()[]')
                # Validate: must be at least 7 characters (e.g., "Jan 2024") or a 4-digit year
                if len(full_match) >= 4:
                    # Filter out fragments: must contain either a complete month name or be a 4-digit year
                    full_match_lower = full_match.lower()
                    valid_months = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december', 'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                    
                    # Check if it contains a valid month name or is a 4-digit year
                    has_valid_month = any(month in full_match_lower for month in valid_months)
                    is_year_only = re.match(r'^\d{4}$', full_match)
                    
                    if has_valid_month or is_year_only:
                        # Exclude fragments: only reject if it's a standalone fragment (not part of a valid month)
                        invalid_fragments = ['ober', 'uary', 'ember', 'tember', 'ruary']
                        # Only reject if the match IS a fragment (not if it contains a valid month)
                        if has_valid_month:
                            # If it contains a valid month, it's not a fragment - accept it
                            all_date_matches.append(full_match)
                        elif is_year_only:
                            # Standalone year - accept it
                            all_date_matches.append(full_match)
                        else:
                            # Check if it's a standalone fragment (not part of a valid date)
                            if not any(fragment == full_match_lower for fragment in invalid_fragments):
                                all_date_matches.append(full_match)
        
        # Remove duplicates and add to entities
        for date in dict.fromkeys(all_date_matches):  # Preserves order while removing duplicates
            if date not in entities['dates']:
                entities['dates'].append(date)
    
    # Pattern-based extraction for better coverage (especially for titles and short texts)
    if extract_persons:
        # Pattern: Capitalized word(s) that look like names (First Last, First Middle Last)
        # Common name patterns: "John Smith", "Mary-Jane Watson", "O'Brien"
        name_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b'
        # Exclude common capitalized words that aren't names
        exclude_words = {
            'The', 'A', 'An', 'In', 'On', 'At', 'For', 'With', 'From', 'To', 'Of', 'And', 'Or', 'But', 'As', 'By',
            'War', 'Prisoner', 'Escape', 'Camp', 'Life', 'Liberation', 'Discover', 'Earn', 'Points', 'Support',
            'Login', 'Vietnam', 'United', 'States', 'America', 'World', 'Documentary', 'Mini', 'Series', 'Trailer',
            'English', 'General', 'Seasons', 'Brasil', 'Crew', 'Artwork', 'Lists', 'Changed',
            'Article', 'Talk', 'Read', 'Tools', 'Appearance', 'Text', 'Small', 'Standard', 'Large', 'Width',
            'Wide', 'Color', 'Automatic', 'Light', 'Dark', 'From', 'Wikipedia', 'Nathu', 'La', 'Cho', 'Indochina', 'Wars',
            # Software and product names
            'Microsoft', 'Word', 'Excel', 'PowerPoint', 'Outlook', 'Windows', 'Macintosh', 'Apple', 'Mac', 'iOS', 'Android',
            'Google', 'Chrome', 'Firefox', 'Safari', 'Edge', 'Internet', 'Explorer', 'Opera', 'Browser',
            'Edit', 'View', 'File', 'Insert', 'Format', 'Tools', 'Table', 'Help', 'Developer', 'Initial', 'Predecessor',
            'Multi', 'Type', 'License', 'Trialware', 'Website', 'Tool', 'Office', 'Media', 'Unix', 'Independent',
            'Wikimedia', 'Foundation', 'Project', 'Wikipedia', 'Meta',
            # UI elements and actions
            'Share', 'Print', 'Save', 'Open', 'Close', 'New', 'Copy', 'Paste', 'Cut', 'Undo', 'Redo', 'Find', 'Replace',
            'Select', 'All', 'None', 'Zoom', 'In', 'Out', 'Fit', 'Page', 'Width', 'Actual', 'Size',
            'Font', 'Size', 'Bold', 'Italic', 'Underline', 'Strikethrough', 'Subscript', 'Superscript',
            'Align', 'Left', 'Center', 'Right', 'Justify', 'Bullet', 'Number', 'List', 'Indent', 'Decrease', 'Increase',
            # Common phrases that look like names
            'Regular', 'Guys', 'Built', 'Wordperfect', 'Eclectic', 'Light',
            # UI instruction words
            'To', 'How', 'Duplicate', 'Pages', 'Page', 'Document', 'If', 'Press', 'Ctrl', 'Blank', 'Break',
            'Different', 'You', 'Sub', 'Enter', 'Number', 'Select', 'Place', 'Your', 'Cursor', 'Want', 'Min', 'Read'
        }
        # Common non-name patterns (articles, titles, UI elements, software names, instructions, etc.)
        non_name_patterns = [
            r'\b(Discover|Support|Login|Earn|Points|The War|That|Changed|America|Brasil|General|Seasons|Crew|Artwork|Lists|Documentary|Mini|Series|United States|English Trailer)\b',
            r'\b[A-Z][a-z]+\s+(Earn|Points|Login|Support|War|That|Changed|America)\b',
            r'\b(The|A|An)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Articles before capitalized words
            r'\b(Article|Talk|Read|Tools|Appearance|Text|Small|Standard|Large|Width|Wide|Color|Automatic|Light|Dark|From|Wikipedia)\s+[A-Z][a-z]+\b',  # UI elements
            r'\b[A-Z][a-z]+\s+(Talk|Read|Tools|Appearance|Text|Small|Standard|Large|Width|Wide|Color)\b',  # UI patterns
            r'\b(Nathu|Cho)\s+La\b',  # Geographic locations
            r'\bIndochina\s+Wars\b',  # Historical events
            # Software and product names
            r'\b(Microsoft|Apple|Google|Windows|Macintosh|Mac|Word|Excel|PowerPoint|Outlook|Chrome|Firefox|Safari|Edge|Internet|Explorer)\s+[A-Z][a-z]+\b',
            r'\b[A-Z][a-z]+\s+(Word|Excel|PowerPoint|Outlook|Windows|Macintosh|Mac|Chrome|Firefox|Safari|Edge|Explorer|Browser|Office|Media|Unix|Developer|Initial|Predecessor|Multi|Type|License|Trialware|Website|Tool)\b',
            r'\b(Edit|View|File|Insert|Format|Tools|Table|Help|Share|Print|Save|Open|Close|New|Copy|Paste|Cut)\s+[A-Z][a-z]+\b',
            r'\b[A-Z][a-z]+\s+(Edit|View|File|Insert|Format|Tools|Table|Help|Share|Print|Save|Open|Close|New|Copy|Paste|Cut)\b',
            # Software-specific patterns
            r'\b(Microsoft|Word|Microsoft Word|Edit View|Tool Word|Developer|Type Word|License Trialware|Website)\b',
            r'\b(Apple|Macintosh|Mac|iOS|Android|Google|Chrome|Firefox|Safari|Edge|Browser)\b',
            # Common non-name phrases
            r'\b(Regular|Guys|Built|Wordperfect|Eclectic|Light)\s+[A-Z][a-z]+\b',
            r'\b[A-Z][a-z]+\s+(Regular|Guys|Built|Wordperfect|Eclectic|Light)\b',
            # UI instruction patterns (common in tutorials)
            r'\b(To|How)\s+[A-Z][a-z]+\b',  # "To How", "To Duplicate"
            r'\b(To|How)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # "To Duplicate Pages"
            r'\b(Duplicate|Select|Enter|Press|Place|Want)\s+(Pages?|Ctrl|Number|Cursor|Your|To)\b',  # "Duplicate Pages", "Press Ctrl", "Enter Number"
            r'\b(Blank|Page|Document|Break|Different)\s+(Page|Document|You|If)\b',  # "Blank Page", "Page Document", "Page Break"
            r'\b(Page|Document|Press|Ctrl|Enter|Place|Cursor|Select)\s+(Document|If|Ctrl|Number|Your|All|Text)\b',  # "Page Document", "Press Ctrl", "Place Your"
            r'\b(Min|Read|Sub|Duplicate)\s+(Read|Duplicate|Enter)\b',  # "Min Read", "Sub Duplicate"
            r'\b[A-Z][a-z]+\s+(Page|Document|Ctrl|Number|Cursor|Read|Duplicate)\b',  # "Want To Duplicate", "Place Your Cursor"
            r'\b(Windows|Command)\s+(Or|Command)\b',  # "(windows) or command"
        ]
        
        name_matches = re.findall(name_pattern, text)
        for match in name_matches:
            # Skip if it matches non-name patterns
            if any(re.search(pattern, match, re.IGNORECASE) for pattern in non_name_patterns):
                continue
            # Exclude if it's a common word or if it's already found by NLTK
            words_in_match = match.split()
            if match not in exclude_words and match not in entities['persons']:
                # If it's two words (First Last), it's likely a name
                # Additional validation: both words should be proper nouns (capitalized)
                if len(words_in_match) >= 2:
                    # Check that both words are capitalized (proper nouns)
                    if all(word[0].isupper() and word[1:].islower() for word in words_in_match):
                        # Additional check: not common title/UI/software words
                        common_non_names = {
                            'the', 'war', 'that', 'changed', 'america', 'support', 'login', 'earn', 'points',
                            'article', 'talk', 'read', 'tools', 'appearance', 'text', 'small', 'standard', 'large',
                            'width', 'wide', 'color', 'automatic', 'light', 'dark', 'from', 'wikipedia', 'nathu',
                            'cho', 'la', 'indochina', 'wars', 'vietnam', 'united', 'states', 'world', 'documentary',
                            # Software and product names
                            'microsoft', 'word', 'excel', 'powerpoint', 'outlook', 'windows', 'macintosh', 'apple', 'mac',
                            'google', 'chrome', 'firefox', 'safari', 'edge', 'internet', 'explorer', 'browser',
                            'edit', 'view', 'file', 'insert', 'format', 'table', 'help', 'developer', 'initial',
                            'predecessor', 'multi', 'type', 'license', 'trialware', 'website', 'tool', 'office',
                            'media', 'unix', 'independent', 'wikimedia', 'foundation', 'project', 'regular', 'guys',
                            'built', 'wordperfect', 'eclectic', 'light',
                            # UI instruction words
                            'to', 'how', 'duplicate', 'page', 'pages', 'document', 'if', 'press', 'ctrl', 'blank',
                            'break', 'different', 'you', 'sub', 'enter', 'number', 'place', 'your', 'cursor',
                            'want', 'min', 'read', 'select', 'copy', 'paste', 'open', 'close', 'save', 'print'
                        }
                        if not any(word.lower() in common_non_names for word in words_in_match):
                            entities['persons'].append(match)
    
    if extract_locations:
        # DO NOT extract nationalities as locations - they are adjectives, not places
        # Only extract actual place names (cities, countries, regions, etc.)
        # Nationalities are filtered out because they're not actionable locations
        
        # Pattern for actual place names: Capitalized place names (cities, countries, regions)
        # This should be primarily handled by NLTK's GPE (Geopolitical Entity) recognition above
        # Additional regex patterns for place names that might be missed
        place_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:City|State|Province|Country|Region|Island|Islands|Republic|Kingdom|Empire)\b',
            r'\b(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:River|Mountain|Lake|Bay|Sea|Ocean|Gulf|Strait)\b',
        ]
        
        for pattern in place_patterns:
            place_matches = re.findall(pattern, text)
            for match in place_matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1]
                # Exclude common non-place words
                if match not in {'The', 'A', 'An', 'United', 'States', 'America'} and match not in entities['locations']:
                    entities['locations'].append(match)
        
        # Note: Nationalities like "American", "British", "Vietnamese" are NOT added as locations
        # They are adjectives describing people, not actual places
    
    # Extract money values using regex
    if extract_money:
        money_pattern = r'\$[\d,]+(?:\.\d{2})?|[\d,]+(?:\.\d{2})?\s*(?:dollars|USD|EUR|€|£|GBP|yen|JPY)'
        money_matches = re.findall(money_pattern, text, re.IGNORECASE)
        entities['money'].extend(money_matches)
    
    # Extract percentages using regex
    if extract_percent:
        percent_pattern = r'\d+(?:\.\d+)?%'
        percent_matches = re.findall(percent_pattern, text)
        entities['percent'].extend(percent_matches)
    
    # Extract time expressions using regex
    if extract_time:
        time_pattern = r'\b(?:0?[1-9]|1[0-2]):[0-5][0-9]\s*(?:AM|PM|am|pm)|(?:0?[0-9]|1[0-9]|2[0-3]):[0-5][0-9]\b|(?:noon|midnight|midday)'
        time_matches = re.findall(time_pattern, text, re.IGNORECASE)
        entities['time'].extend(time_matches)
    
    # Extract facilities using regex (buildings, hospitals, landmarks)
    if extract_facility:
        # Common facility patterns
        facility_patterns = [
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Hospital|Clinic|Medical Center|University|College|School|Building|Tower|Center|Centre|Museum|Library|Stadium|Arena|Theater|Theatre|Airport|Station)',
            r'\b(?:The\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Building|Tower|Center|Centre)',
        ]
        for pattern in facility_patterns:
            facility_matches = re.findall(pattern, text)
            entities['facility'].extend(facility_matches)
    
    return entities

def preprocess_text(text: str, aggressive: bool = False) -> List[str]:
    words = word_tokenize(text.lower())
    filtered_words = [lemmatizer.lemmatize(word) for word in words if word.isalnum() and (not aggressive or word not in stop_words)]
    return filtered_words if filtered_words else ['empty']

def extract_keywords(texts: List[str], num_keywords: int) -> List[str]:
    all_words = []
    for text in texts:
        words = preprocess_text(text, aggressive=True)
        all_words.extend(words)
    all_words = [word for word in all_words if word != 'empty']
    if not all_words:
        logger.warning("No valid words for keyword extraction")
        return []
    word_counts = Counter(all_words)
    top_keywords = [word for word, _ in word_counts.most_common(num_keywords)]
    logger.info(f"Extracted {len(top_keywords)} keywords: {top_keywords}")
    return top_keywords

def lda_model(texts: List[List[str]], num_topics: int, iterations: int) -> List[List[str]]:
    try:
        dictionary = corpora.Dictionary(texts)
        if len(dictionary) < num_topics:
            logger.warning("LDA: Vocabulary too small")
            return []
        corpus = [dictionary.doc2bow(text) for text in texts]
        num_topics = min(num_topics, len(dictionary), len(texts))
        lda = models.LdaModel(corpus, num_topics=num_topics, id2word=dictionary, passes=min(iterations, 5), random_state=42)
        doc_topics = [lda.get_document_topics(doc, minimum_probability=0) for doc in corpus]
        topic_weights = {}
        for doc in doc_topics:
            for topic_id, weight in doc:
                topic_weights[topic_id] = topic_weights.get(topic_id, 0) + weight
        sorted_topics = sorted(topic_weights.items(), key=lambda x: x[1], reverse=True)[:num_topics]
        return [[word for word, _ in lda.show_topic(topic_id, topn=5)] for topic_id, _ in sorted_topics]
    except Exception as e:
        logger.error(f"LDA error: {str(e)}")
        return []

def bertopic_model(texts: List[str], num_topics: int) -> List[List[str]]:
    if not BERTOPIC_AVAILABLE:
        logger.error("BERTopic is not available - cannot use bertopic_model")
        return []
    try:
        model = BERTopic(nr_topics=num_topics, min_topic_size=1, embedding_model="all-MiniLM-L6-v2")
        topics, probs = model.fit_transform(texts)
        topic_info = model.get_topic_info()
        topic_info = topic_info[topic_info['Topic'] != -1].sort_values(by='Count', ascending=False)
        top_n = topic_info.head(min(num_topics, len(topic_info)))
        return [[word for word, _ in model.get_topic(topic_id)[:5]] for topic_id in top_n['Topic']]
    except Exception as e:
        logger.error(f"BERTopic error: {str(e)}")
        return []

def nmf_model(texts: List[str], num_topics: int, iterations: int) -> List[List[str]]:
    if not SKLEARN_AVAILABLE:
        logger.error("NMF model requires sklearn, which is not available")
        return []
    try:
        vectorizer = TfidfVectorizer(max_df=1.0, min_df=1)
        tfidf = vectorizer.fit_transform(texts)
        num_topics = min(num_topics, tfidf.shape[0])
        nmf = NMF(n_components=num_topics, random_state=42, max_iter=iterations)
        W = nmf.fit_transform(tfidf)
        topic_sums = np.sum(W, axis=0)
        top_indices = np.argsort(topic_sums)[::-1][:num_topics]
        feature_names = vectorizer.get_feature_names_out()
        return [[feature_names[i] for i in nmf.components_[idx].argsort()[-5:]] for idx in top_indices]
    except Exception as e:
        logger.error(f"NMF error: {str(e)}")
        return []

def lsa_model(texts: List[str], num_topics: int, iterations: int) -> List[List[str]]:
    if not SKLEARN_AVAILABLE:
        logger.error("LSA model requires sklearn, which is not available")
        return []
    try:
        vectorizer = TfidfVectorizer(max_df=1.0, min_df=1)
        tfidf = vectorizer.fit_transform(texts)
        num_topics = min(num_topics, tfidf.shape[0])
        lsa = TruncatedSVD(n_components=num_topics, n_iter=iterations, random_state=42)
        W = lsa.fit_transform(tfidf)
        topic_sums = np.sum(np.abs(W), axis=0)
        top_indices = np.argsort(topic_sums)[::-1][:num_topics]
        feature_names = vectorizer.get_feature_names_out()
        return [[feature_names[i] for i in lsa.components_[idx].argsort()[-5:]] for idx in top_indices]
    except Exception as e:
        logger.error(f"LSA error: {str(e)}")
        return []

import re

def system_model_topics(texts: List[str], num_topics: int, query: str = "", keywords: List[str] = [], urls: List[str] = []) -> List[str]:
    """
    System model (LLM-free) topic extraction using NMF with Gensim Phrases and spaCy tokenization.
    Loads ALL configuration from system_settings table (fully configurable from admin panel).
    """
    try:
        # Import required libraries
        try:
            # First check if gensim is available at module level
            if not GENSIM_AVAILABLE_TOP_LEVEL:
                # Try importing gensim directly (might have been installed after module load)
                try:
                    import gensim
                    from gensim import corpora, models
                    logger.info(f"✅ Gensim available (imported at function level): {gensim.__version__}")
                except ImportError as e:
                    logger.error(f"❌ Gensim not available - system model requires gensim. Import error: {e}")
                    logger.error("❌ Install with: pip install gensim>=4.3.2 && sudo systemctl restart vernal-agents")
                    return []
            
            from gensim.models import Phrases
            from gensim.models.coherencemodel import CoherenceModel
            # Phraser was removed in gensim 4.x - Phrases can be used directly
            PHRASER_AVAILABLE = False  # Initialize to False (gensim 4.x default)
            try:
                from gensim.models import Phraser
                PHRASER_AVAILABLE = True
            except ImportError:
                # Phraser not available in gensim 4.x - use Phrases directly
                logger.info("ℹ️ Phraser not available (gensim 4.x) - using Phrases directly")
            GENSIM_AVAILABLE = True
            logger.info("✅ Gensim models imported successfully")
        except ImportError as e:
            logger.error(f"❌ Gensim not available - system model requires gensim. Import error: {e}")
            logger.error("❌ Install with: pip install gensim>=4.3.2 && sudo systemctl restart vernal-agents")
            return []
        
        if not SKLEARN_AVAILABLE:
            logger.error("❌ sklearn not available - system model requires sklearn")
            return []
        
        # Check for spaCy (optional but recommended)
        try:
            import spacy
            SPACY_AVAILABLE = True
            try:
                nlp = spacy.load("en_core_web_sm", disable=["ner", "parser", "textcat"])
                nlp.enable_pipe("lemmatizer")
                logger.info("✅ Using spaCy for enhanced tokenization (lemmatization + POS filtering)")
            except OSError:
                logger.warning("⚠️ spaCy model 'en_core_web_sm' not found, falling back to simple tokenization")
                logger.warning("⚠️ Install with: python -m spacy download en_core_web_sm")
                SPACY_AVAILABLE = False
                nlp = None
        except ImportError:
            logger.warning("⚠️ spaCy not available, using simple tokenization")
            SPACY_AVAILABLE = False
            nlp = None
        
        # Load ALL configuration from database (fully configurable)
        try:
            from database import SessionLocal
            from models import SystemSettings
            db = SessionLocal()
            try:
                config = {}
                settings = db.query(SystemSettings).filter(
                    SystemSettings.setting_key.like("system_model_%")
                ).all()
                
                for setting in settings:
                    key = setting.setting_key.replace("system_model_", "")
                    value = setting.setting_value
                    if key == "k_grid":
                        config["K_GRID"] = json.loads(value) if value else [10, 15, 20, 25]
                    elif key in ["phrases_threshold", "tfidf_max_df"]:
                        config[key.upper()] = float(value) if value else (15.0 if key == "phrases_threshold" else 0.7)
                    elif key == "min_doc_len_chars":
                        config["MIN_DOC_LEN_CHARS"] = int(value) if value else 400
                    elif key == "max_per_domain":
                        # None means disabled, otherwise integer
                        config["MAX_PER_DOMAIN"] = int(value) if value and value.lower() != "none" else None
                    elif key == "nmf_max_iter":
                        config["NMF_MAX_ITER"] = int(value) if value else 500
                    elif key == "nmf_random_state":
                        config["NMF_RANDOM_STATE"] = int(value) if value else 42
                    elif key == "use_spacy":
                        config["USE_SPACY"] = value.lower() == "true" if value else True
                    else:
                        config[key.upper()] = int(value) if value else {
                            "phrases_min_count": 5,
                            "tfidf_min_df": 3,
                            "top_words": 12,
                        }.get(key, 0)
                
                # Set defaults for all parameters
                PHRASES_MIN_COUNT = config.get("PHRASES_MIN_COUNT", 5)
                PHRASES_THRESHOLD = config.get("PHRASES_THRESHOLD", 15.0)
                TFIDF_MIN_DF = config.get("TFIDF_MIN_DF", 3)
                TFIDF_MAX_DF = config.get("TFIDF_MAX_DF", 0.7)
                K_GRID = config.get("K_GRID", [10, 15, 20, 25])
                TOP_WORDS = config.get("TOP_WORDS", 12)
                MIN_DOC_LEN_CHARS = config.get("MIN_DOC_LEN_CHARS", 400)
                MAX_PER_DOMAIN = config.get("MAX_PER_DOMAIN", None)
                NMF_MAX_ITER = config.get("NMF_MAX_ITER", 500)
                NMF_RANDOM_STATE = config.get("NMF_RANDOM_STATE", 42)
                USE_SPACY = config.get("USE_SPACY", True) and SPACY_AVAILABLE
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"⚠️ Could not load config from DB, using defaults: {e}")
            PHRASES_MIN_COUNT = 5
            PHRASES_THRESHOLD = 15.0
            TFIDF_MIN_DF = 3
            TFIDF_MAX_DF = 0.7
            K_GRID = [10, 15, 20, 25]
            TOP_WORDS = 12
            MIN_DOC_LEN_CHARS = 400
            MAX_PER_DOMAIN = None
            NMF_MAX_ITER = 500
            NMF_RANDOM_STATE = 42
            USE_SPACY = SPACY_AVAILABLE
        
        # Filter documents by minimum length (removes noise from tiny pages)
        filtered_texts = [t for t in texts if t and len(t.strip()) >= MIN_DOC_LEN_CHARS]
        if len(filtered_texts) < len(texts):
            logger.info(f"📊 Filtered {len(texts) - len(filtered_texts)} documents below {MIN_DOC_LEN_CHARS} chars")
        
        if not filtered_texts:
            logger.warning(f"⚠️ No documents meet minimum length requirement ({MIN_DOC_LEN_CHARS} chars)")
            return []
        
        texts = filtered_texts
        
        # Optional: Domain diversity filtering (if URLs provided)
        if MAX_PER_DOMAIN and urls and len(urls) == len(texts):
            from urllib.parse import urlparse
            from collections import defaultdict
            
            def normalize_domain(u):
                try:
                    d = urlparse(u).netloc.lower()
                    return d[4:] if d.startswith("www.") else d
                except:
                    return ""
            
            # Group texts by domain
            domain_texts = defaultdict(list)
            for text, url in zip(texts, urls):
                domain = normalize_domain(url)
                domain_texts[domain].append((text, url))
            
            # Cap per domain
            filtered_texts = []
            filtered_urls = []
            for domain, items in domain_texts.items():
                # Keep up to MAX_PER_DOMAIN items per domain (keep most recent if sorted)
                for text, url in items[:MAX_PER_DOMAIN]:
                    filtered_texts.append(text)
                    filtered_urls.append(url)
            
            if len(filtered_texts) < len(texts):
                logger.info(f"📊 Domain diversity: {len(texts)} -> {len(filtered_texts)} docs (max {MAX_PER_DOMAIN} per domain)")
            texts = filtered_texts
            urls = filtered_urls if urls else []
        
        # Tokenize documents using spaCy (if available) or simple tokenization
        tokens_list = []
        if USE_SPACY and nlp:
            logger.info("🔍 Using spaCy tokenization (lemmatization + POS filtering)")
            for text in texts:
                doc = nlp(text)
                toks = []
                for tok in doc:
                    if tok.is_punct or tok.is_space or tok.like_num:
                        continue
                    lemma = tok.lemma_.lower().strip()
                    if not lemma or len(lemma) < 2:
                        continue
                    # Keep nouns/verbs/adjectives/adverbs (most meaningful for topics)
                    if tok.pos_ in ("NOUN", "PROPN", "VERB", "ADJ", "ADV"):
                        toks.append(lemma)
                tokens_list.append(toks)
        else:
            logger.info("🔍 Using simple tokenization (spaCy not available)")
            # Simple sentence splitter (for reference, not used in simple mode)
            sent_split = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")
            
            # Simple tokenization - split on whitespace and filter
            stopwords_set = set(stopwords.words('english'))
            for text in texts:
                words = text.lower().split()
                tokens = [w for w in words if w not in stopwords_set and len(w) > 2 and w.isalpha()]
                tokens_list.append(tokens)
        
        if not tokens_list or sum(len(t) for t in tokens_list) < 10:
            logger.warning("⚠️ Insufficient tokens for system model")
            return []
        
        # Phrase mining with Gensim
        # Use string delimiter (not bytes) since tokens_list contains strings
        bigram = Phrases(tokens_list, min_count=PHRASES_MIN_COUNT, threshold=PHRASES_THRESHOLD, delimiter="_")
        trigram = Phrases(bigram[tokens_list], min_count=PHRASES_MIN_COUNT, threshold=PHRASES_THRESHOLD, delimiter="_")
        # In gensim 4.x, Phraser was removed - Phrases can be used directly
        if PHRASER_AVAILABLE:
            bigr = Phraser(bigram)
            trgr = Phraser(trigram)
            tokens_phrased = [trgr[bigr[tok]] for tok in tokens_list]
        else:
            # Use Phrases directly (gensim 4.x compatibility)
            bigr = bigram
            trgr = trigram
            tokens_phrased = [trgr[bigr[tok]] for tok in tokens_list]
        docs_str = [" ".join(t) for t in tokens_phrased]
        
        # Vectorize with TF-IDF
        tfidf = TfidfVectorizer(min_df=TFIDF_MIN_DF, max_df=TFIDF_MAX_DF, strip_accents="unicode")
        X = tfidf.fit_transform(docs_str)
        terms = tfidf.get_feature_names_out()
        idf = tfidf.idf_
        
        # K sweep (pick best by coherence)
        best = None
        best_topic_terms = None
        for K in K_GRID:
            if K > len(texts):
                continue
            try:
                nmf = NMF(n_components=K, init="nndsvd", random_state=NMF_RANDOM_STATE, max_iter=NMF_MAX_ITER)
                W = nmf.fit_transform(X)
                H = nmf.components_
                
                # Calculate coherence
                topic_terms = [[terms[i] for i in comp.argsort()[-TOP_WORDS:]] for comp in H]
                cm = CoherenceModel(topics=topic_terms, texts=tokens_phrased, coherence="c_v")
                coh = cm.get_coherence()
                
                logger.info(f"📊 K={K}, coherence={coh:.3f}")
                
                if (best is None) or (coh > best[0]):
                    best = (coh, K, nmf, W, H)
                    best_topic_terms = topic_terms
            except Exception as e:
                logger.warning(f"⚠️ Error with K={K}: {e}")
                continue
        
        if best is None:
            logger.error("❌ Could not fit any NMF model")
            return []
        
        coherence, K, nmf, W, H = best
        
        # Label topics
        vocab = terms.tolist()
        idf_lookup = {t: idf[i] for i, t in enumerate(vocab)}
        labels = []
        for row in H:
            idx = row.argsort()[-TOP_WORDS:][::-1]
            cand = [(terms[i], row[i]) for i in idx]
            scored = []
            for t, w in cand:
                bonus = 1.3 if "_" in t else 1.0
                scored.append((t, w * idf_lookup.get(t, 1.0) * bonus))
            scored.sort(key=lambda x: x[1], reverse=True)
            title = " / ".join([t.replace("_", " ") for t, _ in scored[:2]]) or (cand[0][0] if cand else "topic")
            labels.append(title[:35])
        
        # Return top topics (limit to num_topics)
        topic_strength = W.sum(axis=0)
        if hasattr(topic_strength, "A1"):
            topic_strength = topic_strength.A1
        order = np.argsort(-topic_strength)
        
        result = [labels[int(t_idx)] for t_idx in order[:num_topics]]
        logger.info(f"✅ System model generated {len(result)} topics: {result[:5]}")
        return result
        
    except Exception as e:
        logger.error(f"❌ System model error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def llm_model(texts: List[str], num_topics: int, query: str = "", keywords: List[str] = [], urls: List[str] = []) -> List[str]:
    try:
        logger.info(f"🔍 llm_model called with {len(texts)} texts, num_topics={num_topics}, query='{query}', keywords={keywords[:3]}")
        
        # Check if langchain_openai is available
        if not LANGCHAIN_OPENAI_AVAILABLE:
            logger.error("❌ langchain_openai is not installed. Install it with: pip install langchain-openai")
            return []
        
        # Check API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ OPENAI_API_KEY not found in environment")
            return []
        logger.info(f"✅ OPENAI_API_KEY found (length: {len(api_key)})")
        
        # Initialize the OpenAI model
        logger.info("🔍 Initializing ChatOpenAI model...")
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=api_key,
            temperature=0.4,  # Slightly higher temperature for creative phrasing
            max_tokens=500    # Limit tokens to keep responses concise
        )
        logger.info("✅ ChatOpenAI model initialized")

        # Prepare the input context with explicit inclusion of scraped texts
        context = "Scraped Texts:\n"
        for i, text in enumerate(texts[:5], 1):  # Limit to first 5 texts to avoid token overflow
            context += f"Text {i}: {text}\n"
        if query:
            context += f"Query: {query}\n"
        if keywords:
            context += f"Keywords: {', '.join(keywords)}\n"
        if urls:
            context += f"URLs: {', '.join(urls)}\n"

        # Load prompt from database, with fallback to default
        prompt_template = get_topic_extraction_prompt()
        
        # Format the prompt with actual values
        prompt = prompt_template.format(num_topics=num_topics, context=context)

        max_attempts = 3
        for attempt in range(max_attempts):
            logger.info(f"🔍 LLM attempt {attempt + 1}/{max_attempts}: Calling OpenAI API...")
            try:
                # Call the LLM
                # Track OpenAI API usage for gas meter
                from gas_meter.openai_wrapper import track_langchain_call
                response = track_langchain_call(llm, model="gpt-4o-mini", prompt=prompt)
                response_text = response.content.strip()
                logger.info(f"✅ LLM API call successful, response length: {len(response_text)}")
                logger.debug(f"🔍 Raw LLM response: {response_text[:200]}...")

                # Robustly strip markdown formatting and extra whitespace
                response_text = re.sub(r'^```json\s*|\s*```$', '', response_text, flags=re.MULTILINE)
                response_text = re.sub(r'^\s*|\s*$', '', response_text)  # Remove leading/trailing whitespace

                # Parse the JSON response
                try:
                    topics = json.loads(response_text)
                    logger.info(f"✅ JSON parsed successfully, got {len(topics) if isinstance(topics, list) else 'non-list'} items")
                    
                    # Validate that topics are a list of strings, each with 2-4 words (NOT single words)
                    if isinstance(topics, list):
                        # Filter out single-word topics and validate
                        valid_topics = []
                        for topic in topics:
                            if isinstance(topic, str):
                                word_count = len(topic.split())
                                # Must be 2-4 words, not a single word
                                if 2 <= word_count <= 4:
                                    valid_topics.append(topic)
                                else:
                                    logger.warning(f"⚠️ Rejected topic '{topic}' - has {word_count} word(s), need 2-4 words")
                        
                        # Additional filtering: remove topics with URLs, file extensions, technical identifiers, or UI instructions
                        filtered_topics = []
                        invalid_patterns = [
                            r'\.(com|org|net|edu|gov|io|isbn|doi|pdf|html|xml|json)',  # URLs, file extensions, identifiers
                            r'^https?://',  # URLs
                            r'^\d+$',  # Pure numbers
                            r'^[a-z]+\.[a-z]+',  # Domain-like patterns (press.isbn)
                        ]
                        # UI instruction patterns (common in tutorials/help content)
                        ui_instruction_patterns = [
                            r'^(press|enter|select|place|click|duplicate|copy|paste|open|close|save|print)\s+',  # Command verbs
                            r'\s+(ctrl|cmd|shift|alt|enter|space|tab|escape|delete|backspace)\b',  # Keyboard keys
                            r'\b(press|enter|select|place|click|duplicate|copy|paste|open|close|save|print)\s+(ctrl|cmd|shift|alt|enter|space|tab|escape|delete|backspace|your|cursor|number|pages?|document|text|all)\b',  # Full instructions
                            r'\b(blank|page|document|break|min|read|want|to|how|if|or)\s+(page|document|break|read|duplicate|pages?|document|if|command)\b',  # Common UI phrases
                            r'^(windows|command)\s+(or|command)\b',  # "(windows) or command"
                            r'\b(place|your|cursor|want|to|duplicate|min|read)\b',  # Common instruction words
                            r'^(page|document|ctrl|number|cursor|read|duplicate)\s+',  # Starting with UI terms
                        ]
                        for topic in valid_topics:
                            topic_lower = topic.lower()
                            # Skip if matches invalid patterns
                            if any(re.search(pattern, topic, re.IGNORECASE) for pattern in invalid_patterns):
                                logger.warning(f"⚠️ Filtered out invalid topic pattern: {topic}")
                                continue
                            # Skip if it's a UI instruction/command
                            if any(re.search(pattern, topic_lower) for pattern in ui_instruction_patterns):
                                logger.warning(f"⚠️ Filtered out UI instruction topic: {topic}")
                                continue
                            # Skip common UI instruction phrases
                            ui_phrases = [
                                'press ctrl', 'press ctrl +', 'place your cursor', 'min read', 'want to duplicate',
                                'blank page', 'page you want', 'duplicate pages', 'windows or command', 'page break',
                                'enter number', 'select all', 'copy paste', 'open file', 'save document'
                            ]
                            if any(phrase in topic_lower for phrase in ui_phrases):
                                logger.warning(f"⚠️ Filtered out UI instruction phrase: {topic}")
                                continue
                            # Skip if it's too short or too long (meaningless)
                            if len(topic.split()) < 2 or len(topic) > 50:
                                continue
                            filtered_topics.append(topic)
                        
                        if len(filtered_topics) >= num_topics:
                            topics = filtered_topics[:num_topics]  # Trim to exactly num_topics
                            logger.info(f"✅ LLM extracted {len(topics)} valid topic phrases: {topics}")
                            return topics
                        elif len(filtered_topics) > 0:
                            # Return what we have even if less than requested
                            logger.warning(f"⚠️ LLM returned only {len(filtered_topics)} valid topics after filtering, need {num_topics}")
                            return filtered_topics
                        else:
                            logger.warning(f"⚠️ LLM attempt {attempt + 1} returned only {len(valid_topics)} valid phrases, need {num_topics}")
                            logger.warning(f"⚠️ Valid topics: {valid_topics}")
                            logger.warning(f"⚠️ All topics: {topics}")
                    else:
                        logger.warning(f"⚠️ LLM attempt {attempt + 1} returned non-list response")
                        logger.warning(f"⚠️ Response was: {response_text[:500]}")
                except json.JSONDecodeError as json_err:
                    logger.error(f"❌ LLM attempt {attempt + 1} response is not valid JSON: {json_err}")
                    logger.error(f"❌ Response text: {response_text[:500]}")
            except Exception as api_err:
                logger.error(f"❌ LLM API call failed on attempt {attempt + 1}: {str(api_err)}")
                logger.error(f"❌ Error type: {type(api_err).__name__}")
                import traceback
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
                if attempt < max_attempts - 1:
                    logger.info("🔄 Retrying LLM call...")
                    continue
                else:
                    raise  # Re-raise on final attempt
            
            if attempt < max_attempts - 1:
                logger.info("🔄 Retrying LLM with adjusted prompt")

        # Fallback if LLM fails to produce valid phrases
        logger.warning("LLM failed to produce valid phrases; generating fallback topics")
        fallback_topics = []
        # Use keywords and extracted keywords to generate fallback topics
        base_words = keywords[:num_topics] if keywords else []
        if len(base_words) < num_topics:
            extra_keywords = extract_keywords(texts, num_topics - len(base_words))
            base_words.extend(extra_keywords)
        for i in range(min(num_topics, len(base_words))):
            fallback_topics.append(f"{base_words[i]} related research")
        # Pad with generic topics if still short
        while len(fallback_topics) < num_topics:
            fallback_topics.append(f"marine topic {len(fallback_topics) + 1}")
        return fallback_topics[:num_topics]

    except Exception as e:
        logger.error(f"❌ LLM model error: {str(e)}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return []

def extract_topics(texts: List[str], topic_tool: Optional[str], num_topics: int, iterations: int, query: str = "", keywords: List[str] = [], urls: List[str] = []) -> List[str]:
    total_words = sum(len(text.strip().split()) for text in texts)
    logger.info(f"Processing {len(texts)} texts with {total_words} words")

    if not texts or total_words < 10:
        logger.warning("Insufficient data; using keyword extraction")
        return extract_keywords(texts, num_keywords=num_topics)

    # Check if system model is requested
    if topic_tool == 'system':
        logger.info("🔍 Using system model (NMF-based with Gensim Phrases) for topic extraction")
        try:
            topics = system_model_topics(texts, num_topics, query, keywords, urls)
            if topics:
                logger.info(f"✅ System model returned {len(topics)} topics")
                return topics
            else:
                logger.warning("⚠️ System model returned empty, falling back to NMF")
                topic_tool = 'nmf'  # Fallback to regular NMF
        except Exception as e:
            logger.error(f"❌ Error in system model: {e}, falling back to NMF")
            import traceback
            logger.error(traceback.format_exc())
            topic_tool = 'nmf'  # Fallback to regular NMF

    # Remove stop words from all texts before processing
    texts_no_stopwords = [remove_stopwords(text) for text in texts]
    preprocessed = [preprocess_text(text, aggressive=len(texts_no_stopwords) > 5) for text in texts_no_stopwords]
    raw_texts = texts_no_stopwords

    # Select model based on topic_tool or run all
    models = {
        'lda': lambda: lda_model(preprocessed, num_topics, iterations),
        'bertopic': lambda: bertopic_model(raw_texts, num_topics),
        'nmf': lambda: nmf_model(raw_texts, num_topics, iterations),
        'lsa': lambda: lsa_model(raw_texts, num_topics, iterations),
    }

    if topic_tool == 'llm':
        # For LLM, call llm_model directly with texts (not preprocessed)
        # CRITICAL: This ALWAYS uses the prompt from database (or default fallback)
        logger.info("🔍 Calling llm_model function... (will use prompt from database)")
        topics = llm_model(texts, num_topics, query, keywords, urls)
        logger.info(f"🔍 llm_model returned: {topics} (type: {type(topics)}, length: {len(topics) if topics else 0})")
        if not topics:
            logger.warning("⚠️ LLM model returned empty result; falling back to phrase extraction from bigrams/trigrams")
            # Fallback to phrase extraction instead of single-word keywords
            # Extract meaningful phrases from texts (same logic as non-LLM fallback)
            # Counter is already imported at the top of the file
            stopwords_set = set(stopwords.words('english'))
            phrases = []
            
            for text in texts[:50]:  # Limit to first 50 texts for performance
                words = text.lower().split()
                # Extract bigrams
                for i in range(len(words) - 1):
                    bigram = f"{words[i]} {words[i+1]}"
                    phrase_words = bigram.split()
                    meaningful_words = [w for w in phrase_words if w not in stopwords_set and len(w) > 2]
                    if len(meaningful_words) >= 2:  # At least 2 meaningful words
                        phrases.append(bigram)
                # Extract trigrams
                for i in range(len(words) - 2):
                    trigram = f"{words[i]} {words[i+1]} {words[i+2]}"
                    phrase_words = trigram.split()
                    meaningful_words = [w for w in phrase_words if w not in stopwords_set and len(w) > 2]
                    if len(meaningful_words) >= 2:  # At least 2 meaningful words
                        phrases.append(trigram)
            
            # Count phrase frequencies and get top phrases
            phrase_counts = Counter(phrases)
            top_phrases = [phrase for phrase, _ in phrase_counts.most_common(num_topics)]
            
            logger.warning(f"⚠️ Using phrase extraction fallback: {top_phrases}")
            return top_phrases if top_phrases else extract_keywords(texts, num_keywords=num_topics)
        logger.info(f"✅ LLM model returned {len(topics)} topics: {topics}")
        return topics
    else:
        # For other models, aggregate words as before
        all_topic_words = []
        if topic_tool and topic_tool in models:
            model_topics = models[topic_tool]()
            all_topic_words.extend([word for topic in model_topics for word in topic])
        else:
            # Run all models if no specific tool is selected
            for model_name, model_func in models.items():
                if model_name != 'llm':  # Exclude LLM for mixed model runs
                    model_topics = model_func()
                    all_topic_words.extend([word for topic in model_topics for word in topic])

        if not all_topic_words:
            logger.warning("All models failed; using keyword extraction")
            return extract_keywords(texts, num_keywords=num_topics)

        # Generate topic phrases instead of single words
        # Extract bigrams and trigrams from original texts that contain the top words
        from collections import defaultdict
        import re
        
        # Find bigrams and trigrams containing the top topic words
        topic_words_set = set(all_topic_words[:20])  # Use top 20 words for context
        phrases = []
        
        for text in raw_texts[:50]:  # Limit to first 50 texts for performance
            words = text.lower().split()
            # Extract bigrams
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                # Check if bigram contains any topic word
                if any(word in bigram for word in topic_words_set):
                    phrases.append(bigram)
            # Extract trigrams
            for i in range(len(words) - 2):
                trigram = f"{words[i]} {words[i+1]} {words[i+2]}"
                # Check if trigram contains any topic word
                if any(word in trigram for word in topic_words_set):
                    phrases.append(trigram)
        
        # Count phrase frequencies
        phrase_counts = Counter(phrases)
        
        # Get top phrases, ensuring they're meaningful (at least 2 words, not too common stopwords)
        stopwords_set = set(stopwords.words('english'))
        top_phrases = []
        for phrase, count in phrase_counts.most_common(num_topics * 3):  # Get more candidates
            # Filter out phrases that are just stopwords
            phrase_words = phrase.split()
            meaningful_words = [w for w in phrase_words if w not in stopwords_set and len(w) > 2]
            if len(meaningful_words) >= 2:  # At least 2 meaningful words
                top_phrases.append(phrase)
                if len(top_phrases) >= num_topics:
                    break
        
        # If we have good phrases, use them; otherwise fall back to single words
        if top_phrases:
            logger.info(f"Generated {len(top_phrases)} topic phrases: {top_phrases}")
            return top_phrases[:num_topics]
        else:
            # Fallback to single words
            word_counts = Counter(all_topic_words)
            top_words = [word for word, _ in word_counts.most_common(num_topics)]
            logger.info(f"Generated {len(top_words)} topics (single words): {top_words}")
            return top_words if top_words else extract_keywords(texts, num_keywords=num_topics)