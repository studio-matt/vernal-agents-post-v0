from pydantic import BaseModel
from typing import List, Optional, Dict
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer, PorterStemmer
from nltk.corpus import stopwords
from nltk import pos_tag, ne_chunk
import gensim
from gensim import corpora, models
from bertopic import BERTopic
from sklearn.decomposition import NMF, TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import Counter
import numpy as np
import logging
from langchain_openai import ChatOpenAI
import os
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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

def extract_entities(text: str, extract_persons: bool, extract_organizations: bool, extract_locations: bool, extract_dates: bool) -> Dict[str, List[str]]:
    entities = {
        'persons': [],
        'organizations': [],
        'locations': [],
        'dates': []
    }
    if not any([extract_persons, extract_organizations, extract_locations, extract_dates]):
        return entities

    words = word_tokenize(text)
    pos_tags = pos_tag(words)
    chunks = ne_chunk(pos_tags)

    for chunk in chunks:
        if hasattr(chunk, 'label'):
            entity_type = chunk.label()
            entity_text = ' '.join(c[0] for c in chunk)
            if entity_type == 'PERSON' and extract_persons:
                entities['persons'].append(entity_text)
            elif entity_type == 'ORGANIZATION' and extract_organizations:
                entities['organizations'].append(entity_text)
            elif entity_type == 'GPE' and extract_locations:
                entities['locations'].append(entity_text)
            elif entity_type == 'DATE' and extract_dates:
                entities['dates'].append(entity_text)
    return entities

def preprocess_text(text: str, aggressive: bool = False) -> List[str]:
    words = word_tokenize(text.lower())
    filtered_words = [lemmatizer.lemmatize(word) for word in words if word.isalnum() and (not aggressive or word not in stop_words)]
    return filtered_words if filtered_words else ['empty']

def extract_entities(text: str, extract_persons: bool, extract_organizations: bool, extract_locations: bool, extract_dates: bool) -> dict:
    # Placeholder for extract_entities function
    return {}

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
        # Initialize the OpenAI model
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.4,  # Slightly higher temperature for creative phrasing
            max_tokens=500    # Limit tokens to keep responses concise
        )

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
        You are an expert in topic modeling. Given the following scraped texts, query, keywords, and URLs, identify exactly {num_topics} key topics that are highly relevant to all provided inputs. Each topic must be a concise 3-4 word phrase that is meaningful, stands alone as an important theme, and captures the essence of the content. Topics must not be single words or vague terms; they should form coherent phrases that reflect specific themes. Ensure the topics are distinct and prioritize relevance to the scraped texts, query, keywords, and URLs. Return the result as a JSON array of strings, where each string is a 3-4 word topic phrase. Do not include explanations, additional text, or markdown formatting (e.g., ```json), just the JSON array.

        Example output:
        ["whale communication research", "humpback whale behavior", "AI in marine biology"]

        Context:
        {context}
        """

        max_attempts = 3
        for attempt in range(max_attempts):
            # Call the LLM
            response = llm.invoke(prompt)
            response_text = response.content.strip()

            # Robustly strip markdown formatting and extra whitespace
            response_text = re.sub(r'^```json\s*|\s*```$', '', response_text, flags=re.MULTILINE)
            response_text = re.sub(r'^\s*|\s*$', '', response_text)  # Remove leading/trailing whitespace

            # Parse the JSON response
            try:
                topics = json.loads(response_text)
                # Validate that topics are a list of strings, each with 2-4 words
                if (isinstance(topics, list) and 
                    all(isinstance(topic, str) and 2 <= len(topic.split()) <= 4 for topic in topics) and
                    len(topics) >= num_topics):
                    topics = topics[:num_topics]  # Trim to exactly num_topics
                    logger.info(f"LLM extracted {len(topics)} topics: {topics}")
                    return topics
                else:
                    logger.warning(f"LLM attempt {attempt + 1} returned invalid topic format: {response_text}")
            except json.JSONDecodeError:
                logger.error(f"LLM attempt {attempt + 1} response is not valid JSON: {response_text}")
            
            if attempt < max_attempts - 1:
                logger.info("Retrying LLM with adjusted prompt")

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
        logger.error(f"LLM model error: {str(e)}")
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
        'llm': lambda: llm_model(raw_texts, num_topics, query, keywords, urls)
    }

    if topic_tool == 'llm':
        # For LLM, return the topic phrases directly
        topics = models['llm']()
        if not topics:
            logger.warning("LLM model failed; using keyword extraction")
            return extract_keywords(texts, num_keywords=num_topics)
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

        # Aggregate frequent words
        word_counts = Counter(all_topic_words)
        top_words = [word for word, _ in word_counts.most_common(num_topics)]
        logger.info(f"Generated {len(top_words)} topics: {top_words}")
        return top_words if top_words else extract_keywords(texts, num_keywords=num_topics)