from pydantic import BaseModel
from typing import List, Optional, Dict
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer, PorterStemmer
from nltk.corpus import stopwords
from nltk import pos_tag, ne_chunk
import gensim
from gensim import corpora, models
from collections import Counter
import numpy as np
import logging
import os
import json

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
                entities['persons'].append(entity_text)
            elif entity_type == 'ORGANIZATION' and extract_organizations:
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
        # Comprehensive date patterns - only complete dates
        date_patterns = [
            # Month Day, Year (e.g., "January 15, 2024", "Jan 15 2024")
            r'\b(?:Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|Sep(tember)?|Oct(ober)?|Nov(ember)?|Dec(ember)?)\s+\d{1,2},?\s+\d{4}\b',
            # Month Year (e.g., "January 2024", "Jan 2024")
            r'\b(?:Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|Sep(tember)?|Oct(ober)?|Nov(ember)?|Dec(ember)?)\s+\d{4}\b',
            # MM/DD/YYYY or DD-MM-YYYY (e.g., "01/15/2024", "15-01-2024")
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',
            # YYYY/MM/DD (e.g., "2024/01/15")
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',
            # Ordinal dates (e.g., "15th of January 2024", "the 15th of January 2024")
            r'\b(?:the\s+)?\d{1,2}(?:st|nd|rd|th)\s+(?:of\s+)?(?:Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|Sep(tember)?|Oct(ober)?|Nov(ember)?|Dec(ember)?)\s+\d{4}\b',
            # Years (only if they're clearly dates, not just numbers)
            r'\b(?:in\s+)?(19|20)\d{2}(?:\s|$|\.|,|;|\)|\])\b',  # Years with context
        ]
        for pattern in date_patterns:
            date_matches = re.findall(pattern, text, re.IGNORECASE)
            for match in date_matches:
                if isinstance(match, tuple):
                    # Handle groups - reconstruct full date
                    if len(match) == 2 and match[0] in ['19', '20']:
                        # Year pattern - reconstruct full year
                        full_year = match[0] + match[1] if match[1] else match[0]
                        if len(full_year) == 4:
                            match = full_year
                        else:
                            continue
                    else:
                        # Other patterns - join non-empty parts
                        match = ' '.join(m for m in match if m)
                if match and len(match) >= 4:  # Minimum: year (4 digits) or "Jan 2024" (7 chars)
                    # Clean up the match
                    match = match.strip('.,;()[]')
                    if match not in entities['dates']:
                        entities['dates'].append(match)
    
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
            'Wide', 'Color', 'Automatic', 'Light', 'Dark', 'From', 'Wikipedia', 'Nathu', 'La', 'Cho', 'Indochina', 'Wars'
        }
        # Common non-name patterns (articles, titles, UI elements, etc.)
        non_name_patterns = [
            r'\b(Discover|Support|Login|Earn|Points|The War|That|Changed|America|Brasil|General|Seasons|Crew|Artwork|Lists|Documentary|Mini|Series|United States|English Trailer)\b',
            r'\b[A-Z][a-z]+\s+(Earn|Points|Login|Support|War|That|Changed|America)\b',
            r'\b(The|A|An)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Articles before capitalized words
            r'\b(Article|Talk|Read|Tools|Appearance|Text|Small|Standard|Large|Width|Wide|Color|Automatic|Light|Dark|From|Wikipedia)\s+[A-Z][a-z]+\b',  # UI elements
            r'\b[A-Z][a-z]+\s+(Talk|Read|Tools|Appearance|Text|Small|Standard|Large|Width|Wide|Color)\b',  # UI patterns
            r'\b(Nathu|Cho)\s+La\b',  # Geographic locations
            r'\bIndochina\s+Wars\b',  # Historical events
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
                        # Additional check: not common title/UI words
                        common_non_names = {
                            'the', 'war', 'that', 'changed', 'america', 'support', 'login', 'earn', 'points',
                            'article', 'talk', 'read', 'tools', 'appearance', 'text', 'small', 'standard', 'large',
                            'width', 'wide', 'color', 'automatic', 'light', 'dark', 'from', 'wikipedia', 'nathu',
                            'cho', 'la', 'indochina', 'wars', 'vietnam', 'united', 'states', 'world', 'documentary'
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

        # Craft the prompt for topic extraction
        prompt = f"""
        You are an expert in topic modeling. Your task is to review the scraped information and extract a list of salient topic names as short, descriptive phrases.

        CRITICAL REQUIREMENTS:
        - Each topic MUST be a short, descriptive phrase (2-4 words) that captures a distinct concept
        - Each topic name should be a multi-word phrase if that improves clarity
        - Examples of good topics: 'football offense', 'public health policy', 'gun violence', 'vietnam war history', 'military strategy analysis'
        - NEVER return single words (e.g., "war", "vietnam", "football", "health" are INVALID)
        - Each phrase must be meaningful, descriptive, and stand alone as an important theme
        - Phrases should reflect specific concepts found in the scraped content, not vague terms
        - Ensure topics are distinct and capture different aspects of the content
        - Prioritize topics that are most relevant to the scraped texts, query, keywords, and URLs

        Return EXACTLY {num_topics} topics as a JSON array of strings. Each string must be a 2-4 word descriptive phrase. Do not include explanations, additional text, or markdown formatting (e.g., ```json), just the JSON array.

        Example VALID output:
        ["vietnam war history", "military strategy analysis", "cold war politics", "southeast asia conflict", "combat operations planning"]

        Example INVALID output (DO NOT DO THIS):
        ["war", "vietnam", "history", "military", "strategy"]  ← These are single words, NOT valid

        Context:
        {context}
        """

        max_attempts = 3
        for attempt in range(max_attempts):
            logger.info(f"🔍 LLM attempt {attempt + 1}/{max_attempts}: Calling OpenAI API...")
            try:
                # Call the LLM
                response = llm.invoke(prompt)
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
                        
                        if len(valid_topics) >= num_topics:
                            topics = valid_topics[:num_topics]  # Trim to exactly num_topics
                            logger.info(f"✅ LLM extracted {len(topics)} valid topic phrases: {topics}")
                            return topics
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
        logger.info("🔍 Calling llm_model function...")
        topics = llm_model(texts, num_topics, query, keywords, urls)
        logger.info(f"🔍 llm_model returned: {topics} (type: {type(topics)}, length: {len(topics) if topics else 0})")
        if not topics:
            logger.warning("⚠️ LLM model returned empty result; falling back to phrase extraction from bigrams/trigrams")
            # Fallback to phrase extraction instead of single-word keywords
            # Extract meaningful phrases from texts (same logic as non-LLM fallback)
            from collections import Counter
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