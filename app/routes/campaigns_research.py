"""
Campaign research and analysis endpoints extracted from main.py
Moved from main.py to preserve API contract parity
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from auth_api import get_current_user
from database import SessionLocal

logger = logging.getLogger(__name__)

campaigns_research_router = APIRouter()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Import get_openai_api_key from main (TODO: move to app/utils in future refactor)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from main import get_openai_api_key

@campaigns_research_router.get("/campaigns/{campaign_id}/research")
def get_campaign_research(campaign_id: str, limit: int = 20, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Aggregate research outputs for a campaign.
    - urls: list of source_url
    - raw: up to `limit` extracted_text samples
    - wordCloud: top 10 terms by frequency (cached in DB)
    - topics: naive primary topics (top terms) (cached in DB)
    - entities: NLTK-based extraction using named entity recognition (cached in DB)
    - hashtags: generated from topics/keywords (cached in DB)
    
    Caches wordCloud, topics, hashtags, and entities in database to avoid re-computation.
    REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION
    """
    # Verify campaign ownership
    from models import Campaign
    campaign = db.query(Campaign).filter(
        Campaign.campaign_id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found or access denied"
        )
    
    try:
        from models import CampaignRawData, CampaignResearchData
        import json
        
        # Check if cached research data exists
        cached_data = db.query(CampaignResearchData).filter(
            CampaignResearchData.campaign_id == campaign_id
        ).first()
        
        # Only use cache if it has valid non-empty data
        if cached_data and cached_data.word_cloud_json and cached_data.topics_json:
            try:
                word_cloud = json.loads(cached_data.word_cloud_json) if cached_data.word_cloud_json else []
                topics = json.loads(cached_data.topics_json) if cached_data.topics_json else []
                # Only use cache if we have actual data (not empty arrays)
                if word_cloud and len(word_cloud) > 0 and topics and len(topics) > 0:
                    logger.info(f"✅ Returning cached research data for campaign {campaign_id} (wordCloud: {len(word_cloud)} items, topics: {len(topics)} items)")
                    hashtags = json.loads(cached_data.hashtags_json) if cached_data.hashtags_json else []
                    entities = json.loads(cached_data.entities_json) if cached_data.entities_json else {}
                    
                    # Still need to get URLs and raw text (these change with scraping)
                    rows = db.query(CampaignRawData).filter(CampaignRawData.campaign_id == campaign_id).all()
                    urls = [r.source_url for r in rows if r.source_url and not r.source_url.startswith(("error:", "placeholder:"))]
                    texts = [r.extracted_text for r in rows if r.extracted_text and len(r.extracted_text.strip()) > 0 and not (r.source_url and r.source_url.startswith(("error:", "placeholder:")))]
                    
                    return {
                        "status": "success",
                        "campaign_id": campaign_id,
                        "urls": urls,
                        "raw": texts[:max(0, limit) or 20],
                        "wordCloud": word_cloud,
                        "topics": topics,
                        "hashtags": hashtags,
                        "entities": entities,
                        "total_raw": len(texts),
                        "cached": True,
                        "diagnostics": {
                            "total_rows": len(rows),
                            "valid_urls": len(urls),
                            "valid_texts": len(texts),
                            "has_data": len(urls) > 0 or len(texts) > 0,
                            "cached": True
                        }
                    }
                else:
                    logger.warning(f"⚠️ Cached data exists but is empty (wordCloud: {len(word_cloud) if word_cloud else 0}, topics: {len(topics) if topics else 0}), regenerating...")
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Failed to parse cached JSON data: {e}, regenerating...")
        # Import NLTK-based text processing (lazy import with fallback)
        try:
            from text_processing import (
                extract_entities as nltk_extract_entities,
                remove_stopwords,
                extract_keywords,
                extract_topics
            )
        except ImportError as import_err:
            logger.warning(f"⚠️ text_processing module not available: {import_err}")
            # Define fallback functions
            def nltk_extract_entities(text, **kwargs):
                return {}
            def remove_stopwords(text):
                return text
            def extract_keywords(text):
                return []
            def extract_topics(texts, topic_tool, num_topics, iterations, query="", keywords=[], urls=[]):
                return []

        rows = db.query(CampaignRawData).filter(CampaignRawData.campaign_id == campaign_id).all()
        logger.info(f"🔍 Research endpoint: Found {len(rows)} rows for campaign {campaign_id}")
        urls = []
        texts = []
        errors = []  # Collect error diagnostics
        error_meta = []  # Collect error metadata
        truncation_info = []  # Track which texts were truncated
        
        for r in rows:
            # Check if this is an error/placeholder row
            is_error = r.source_url and r.source_url.startswith(("error:", "placeholder:"))
            
            if is_error:
                # Extract error information
                error_info = {
                    "type": r.source_url,
                    "message": r.extracted_text or "Unknown error",
                    "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None
                }
                # Try to parse meta_json for additional error details
                if r.meta_json:
                    try:
                        meta = json.loads(r.meta_json)
                        error_info["meta"] = meta
                    except:
                        pass
                errors.append(error_info)
                logger.warning(f"⚠️ Found error row: {r.source_url} - {r.extracted_text[:100] if r.extracted_text else 'No message'}")
            else:
                # Valid scraped data
                if r.source_url and not r.source_url.startswith(("error:", "placeholder:")):
                    urls.append(r.source_url)
                # More lenient text check - include text if it exists and has some content (even if short)
                # This helps with campaigns that previously had data but might have shorter snippets
                if r.extracted_text and len(r.extracted_text.strip()) > 0:
                    texts.append(r.extracted_text)  # Keep as string for backward compatibility
                    
                    # Check if this text was truncated (from metadata)
                    if r.meta_json:
                        try:
                            meta = json.loads(r.meta_json)
                            if meta.get("text_truncated", False):
                                truncation_info.append({
                                    "url": r.source_url,
                                    "stored_length": len(r.extracted_text),
                                    "original_length": meta.get("original_length"),
                                    "truncated_by": meta.get("original_length", 0) - len(r.extracted_text) if meta.get("original_length") else 0
                                })
                        except:
                            pass
        
        logger.info(f"🔍 Research endpoint: Extracted {len(urls)} URLs, {len(texts)} text samples, {len(errors)} error rows")
        
        # Enhanced diagnostics logging
        if len(rows) == 0:
            logger.warning(f"⚠️ No rows found in database for campaign {campaign_id}")
        elif len(texts) == 0:
            logger.warning(f"⚠️ No valid text data found for campaign {campaign_id}")
            logger.warning(f"⚠️ Total rows: {len(rows)}, Error rows: {len(errors)}, Valid URLs: {len(urls)}")
            if len(errors) > 0:
                logger.warning(f"⚠️ Error details: {errors[:3]}")  # Log first 3 errors
            # Log sample of rows to understand what's in the DB
            for i, r in enumerate(rows[:5]):
                text_len = len(r.extracted_text) if r.extracted_text else 0
                logger.warning(f"⚠️ Row {i+1}: source_url={r.source_url[:50] if r.source_url else 'None'}, text_length={text_len}, is_error={r.source_url and r.source_url.startswith(('error:', 'placeholder:')) if r.source_url else False}")

        # Campaign ownership already verified above
        # Get campaign info for better topic extraction
        campaign_query = campaign.query if campaign else ""
        campaign_keywords = campaign.keywords.split(",") if campaign and campaign.keywords else []
        campaign_urls = campaign.urls.split(",") if campaign and campaign.urls else []

        # Use extract_topics for phrase-based topics instead of single words
        if texts and len(texts) > 0:
            try:
                # Check topic extraction method from system settings (default to "system")
                from models import SystemSettings
                method_setting = db.query(SystemSettings).filter(
                    SystemSettings.setting_key == "topic_extraction_method"
                ).first()
                
                topic_extraction_method = "system"  # Default to system model
                if method_setting and method_setting.setting_value:
                    topic_extraction_method = method_setting.setting_value.lower()
                
                # Determine topic_tool based on method
                if topic_extraction_method == "llm":
                    # Check if OpenAI API key is available for LLM model
                    openai_key = get_openai_api_key(current_user=None, db=db)
                    if openai_key:
                        topic_tool = "llm"  # Use LLM for phrase generation
                        logger.info("✅ Using LLM model for topics (from system settings)")
                    else:
                        topic_tool = "system"  # Fallback to system model if no API key
                        logger.warning("⚠️ LLM selected but OpenAI API key not found, using system model")
                else:
                    topic_tool = "system"  # Use system model (NMF-based)
                    logger.info("✅ Using system model for topics (from system settings)")
                
                num_topics = 10
                iterations = 25
                
                logger.info(f"🔍 Calling extract_topics with {len(texts)} texts, tool={topic_tool}, num_topics={num_topics}")
                logger.info(f"🔍 Campaign context: query='{campaign_query}', keywords={campaign_keywords[:3]}, urls={len(campaign_urls)}")
                
                topic_phrases = extract_topics(
                    texts,
                    topic_tool=topic_tool,
                    num_topics=num_topics,
                    iterations=iterations,
                    query=campaign_query,
                    keywords=campaign_keywords,
                    urls=campaign_urls
                )
                
                logger.info(f"🔍 extract_topics returned {len(topic_phrases) if topic_phrases else 0} topics: {topic_phrases[:5] if topic_phrases else 'NONE'}")
                
                # If we got phrases, use them; otherwise fall back to word frequency
                if topic_phrases and len(topic_phrases) > 0:
                    # Create topics with scores (use position as proxy for relevance)
                    topics = [{"label": phrase, "score": len(topic_phrases) - i} for i, phrase in enumerate(topic_phrases[:10])]
                    logger.info(f"✅ Generated {len(topics)} topic phrases: {[t['label'] for t in topics]}")
                else:
                    # Fallback to word frequency if extract_topics fails
                    logger.warning(f"⚠️ extract_topics returned no results (texts: {len(texts)}, tool: {topic_tool}), falling back to phrase extraction")
                    # Don't raise exception - continue to fallback logic below
                    topic_phrases = None
                    
            except Exception as topic_err:
                logger.error(f"❌ Error extracting topics with extract_topics: {topic_err}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                logger.warning(f"⚠️ Falling back to phrase extraction due to error")
                topic_phrases = None  # Ensure we go to fallback
                
            # Fallback: Extract meaningful bigrams/trigrams if extract_topics failed or returned empty
            if not topic_phrases or len(topic_phrases) == 0:
                logger.info(f"🔄 Using fallback phrase extraction (extract_topics returned empty or failed)")
                # Fallback: Extract meaningful bigrams/trigrams instead of single words
                from collections import Counter
                from nltk.corpus import stopwords
                from nltk.tokenize import word_tokenize
                from nltk import pos_tag
                
                nltk_stopwords = set(stopwords.words('english'))
                additional_stopwords = {
                    'who', 'which', 'what', 'when', 'where', 'why', 'how', 'but', 'than', 'that', 'this',
                    'these', 'those', 'united', 'world', 'one', 'two', 'also', 'more', 'most', 'very'
                }
                comprehensive_stopwords = nltk_stopwords | additional_stopwords
                
                # Extract meaningful bigrams and trigrams
                phrases = []
                for t in texts[:50]:  # Limit for performance
                    try:
                        tokens = word_tokenize(t.lower())
                        tagged = pos_tag(tokens)
                        # Filter out stopwords and function words
                        meaningful_tokens = [word for word, tag in tagged 
                                           if word not in comprehensive_stopwords 
                                           and tag not in {'PRP', 'PRP$', 'DT', 'IN', 'CC', 'TO'}
                                           and len(word) >= 3 and word.isalpha()]
                        
                        # Extract bigrams
                        for i in range(len(meaningful_tokens) - 1):
                            bigram = f"{meaningful_tokens[i]} {meaningful_tokens[i+1]}"
                            phrases.append(bigram)
                        # Extract trigrams
                        for i in range(len(meaningful_tokens) - 2):
                            trigram = f"{meaningful_tokens[i]} {meaningful_tokens[i+1]} {meaningful_tokens[i+2]}"
                            phrases.append(trigram)
                    except Exception as e:
                        logger.debug(f"Phrase extraction failed for text: {e}")
                        continue
                
                # Count phrase frequencies
                phrase_counts = Counter(phrases)
                top_phrases = phrase_counts.most_common(10)
                
                if top_phrases:
                    topics = [{"label": phrase, "score": count} for phrase, count in top_phrases]
                    logger.info(f"✅ Generated {len(topics)} fallback topic phrases: {[t['label'] for t in topics]}")
                else:
                    # Last resort: single meaningful words
                    word_counts = Counter()
                    for t in texts:
                        try:
                            tokens = word_tokenize(t.lower())
                            tagged = pos_tag(tokens)
                            for word, tag in tagged:
                                if (word not in comprehensive_stopwords and 
                                    tag not in {'PRP', 'PRP$', 'DT', 'IN', 'CC', 'TO'}
                                    and len(word) >= 4 and word.isalpha()):
                                    word_counts[word] += 1
                        except:
                            continue
                    top_words = word_counts.most_common(10)
                    topics = [{"label": word, "score": count} for word, count in top_words]
                    logger.warning(f"⚠️ Using single-word fallback: {[t['label'] for t in topics]}")
        else:
            topics = []
            logger.warning(f"⚠️ No texts available for topic extraction (texts length: {len(texts)})")
            if len(rows) > 0:
                logger.warning(f"⚠️ Campaign has {len(rows)} rows but {len(texts)} valid texts. Error rows: {len(errors)}")
        
        # Build word cloud with comprehensive stopword filtering and POS tagging
        # Use NLTK's comprehensive stopword list + additional filtering
        from nltk.corpus import stopwords
        from nltk.tokenize import word_tokenize
        from nltk import pos_tag
        
        # Comprehensive stopword set (NLTK + common function words)
        nltk_stopwords = set(stopwords.words('english'))
        additional_stopwords = {
            'who', 'which', 'what', 'when', 'where', 'why', 'how', 'but', 'than', 'that', 'this',
            'these', 'those', 'united', 'world', 'one', 'two', 'also', 'more', 'most', 'very',
            'much', 'many', 'some', 'any', 'all', 'each', 'every', 'both', 'few', 'other',
            'such', 'only', 'just', 'even', 'still', 'yet', 'already', 'never', 'always',
            'often', 'sometimes', 'usually', 'generally', 'particularly', 'especially',
            'however', 'therefore', 'thus', 'hence', 'moreover', 'furthermore', 'nevertheless'
        }
        comprehensive_stopwords = nltk_stopwords | additional_stopwords
        
        # Function word POS tags to exclude (pronouns, determiners, prepositions, conjunctions, etc.)
        function_word_tags = {'PRP', 'PRP$', 'DT', 'IN', 'CC', 'TO', 'WDT', 'WP', 'WP$', 'WRB', 'PDT', 'RP', 'EX'}
        
        counts = {}
        for t in texts:
            try:
                # Tokenize and POS tag
                tokens = word_tokenize(t.lower())
                tagged = pos_tag(tokens)
                
                for word, tag in tagged:
                    # Skip if stopword, function word, or too short
                    if (word.lower() in comprehensive_stopwords or 
                        tag in function_word_tags or 
                        len(word) < 3 or 
                        not word.isalpha()):
                        continue
                    counts[word.lower()] = counts.get(word.lower(), 0) + 1
            except Exception as e:
                # Fallback to simple tokenization if NLTK fails
                logger.debug(f"POS tagging failed for text, using simple tokenization: {e}")
                tokenizer = re.compile(r"[A-Za-z]{3,}")
                for w in tokenizer.findall(t.lower()):
                    if w not in comprehensive_stopwords:
                        counts[w] = counts.get(w, 0) + 1
        
        top_terms = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
        word_cloud = [{"term": k, "count": v} for k, v in top_terms]
        
        if not word_cloud or len(word_cloud) == 0:
            logger.warning(f"⚠️ Word cloud generation failed - no terms found. Texts: {len(texts)}, Total chars: {sum(len(t) for t in texts)}")
            # Fallback: use simple word frequency if POS tagging failed
            simple_counts = {}
            for t in texts:
                words = re.findall(r"[A-Za-z]{3,}", t.lower())
                for w in words:
                    if w not in comprehensive_stopwords:
                        simple_counts[w] = simple_counts.get(w, 0) + 1
            top_simple = sorted(simple_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
            word_cloud = [{"term": k, "count": v} for k, v in top_simple]
            logger.info(f"📊 Word cloud (fallback): {[t['term'] for t in word_cloud]}")
        else:
            logger.info(f"📊 Word cloud generated: {len(word_cloud)} terms - {[t['term'] for t in word_cloud[:5]]}")

        # Use NLTK-based entity extraction for accurate named entity recognition
        persons = []
        organizations = []
        locations = []
        dates = []
        money = []
        percent = []
        time = []
        facility = []
        
        # Process texts with NLTK entity extraction
        texts_processed = 0
        texts_skipped = 0
        extraction_errors = 0
        logger.info(f"🔍 Starting entity extraction for {len(texts)} texts (processing up to 100)")
        
        # Log first few texts for debugging
        if len(texts) > 0:
            logger.info(f"📄 Sample text (first 200 chars): {texts[0][:200] if texts[0] else 'EMPTY'}")
        
        for idx, t in enumerate(texts[:100]):
            if not t or len(t.strip()) < 10:
                texts_skipped += 1
                if texts_skipped <= 3:
                    logger.debug(f"⏭️ Skipping text {idx}: length={len(t) if t else 0}")
                continue
            try:
                entity_result = nltk_extract_entities(
                    t,
                    extract_persons=True,
                    extract_organizations=True,
                    extract_locations=True,
                    extract_dates=True,
                    extract_money=True,
                    extract_percent=True,
                    extract_time=True,
                    extract_facility=True
                )
                texts_processed += 1
                
                # Log entities found in this text (first few texts only)
                if texts_processed <= 3:
                    found_entities = {k: len(v) for k, v in entity_result.items() if v}
                    if found_entities:
                        logger.info(f"📝 Text {texts_processed}: Found {found_entities}")
                        # Log sample entities
                        for entity_type, entity_list in entity_result.items():
                            if entity_list:
                                logger.info(f"   {entity_type}: {entity_list[:3]}")
                    else:
                        logger.warning(f"⚠️ Text {texts_processed}: No entities found (length: {len(t)})")
                
                persons.extend(entity_result.get('persons', []))
                organizations.extend(entity_result.get('organizations', []))
                locations.extend(entity_result.get('locations', []))
                dates.extend(entity_result.get('dates', []))
                money.extend(entity_result.get('money', []))
                percent.extend(entity_result.get('percent', []))
                time.extend(entity_result.get('time', []))
                facility.extend(entity_result.get('facility', []))
            except Exception as e:
                extraction_errors += 1
                logger.error(f"❌ Error extracting entities from text {idx} (length {len(t) if t else 0}): {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Fallback to regex for dates if NLTK fails
                try:
                    date_regex = re.compile(r"\b(\d{4}|\d{1,2}/\d{1,2}/\d{2,4}|Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|Sep(tember)?|Oct(ober)?|Nov(ember)?|Dec(ember)?)\s+\d{4}\b", re.I)
                    date_matches = date_regex.findall(t)
                    dates.extend([d[0] if isinstance(d, tuple) else d for d in date_matches])
                except Exception as regex_err:
                    logger.debug(f"Regex fallback also failed: {regex_err}")
        
        logger.info(f"✅ Entity extraction complete: {texts_processed} processed, {texts_skipped} skipped, {extraction_errors} errors")
        
        entities = {
            "persons": list(dict.fromkeys(persons))[:20],
            "organizations": list(dict.fromkeys(organizations))[:20],
            "locations": list(dict.fromkeys(locations))[:20],
            "dates": list(dict.fromkeys(dates))[:20],
            "money": list(dict.fromkeys(money))[:20],
            "percent": list(dict.fromkeys(percent))[:20],
            "time": list(dict.fromkeys(time))[:20],
            "facility": list(dict.fromkeys(facility))[:20],
        }
        
        # Log summary of extracted entities
        total_entities = sum(len(v) for v in entities.values())
        logger.info(f"📊 Extracted {total_entities} total entities: "
                   f"{len(entities['persons'])} persons, "
                   f"{len(entities['organizations'])} organizations, "
                   f"{len(entities['locations'])} locations, "
                   f"{len(entities['dates'])} dates")
        
        # Generate hashtags from topics and keywords (for caching)
        hashtags = []
        if topics:
            for i, topic in enumerate(topics[:10]):
                topic_label = topic.get('label', topic) if isinstance(topic, dict) else str(topic)
                hashtag_name = f"#{topic_label.replace(' ', '')}"
                hashtags.append({
                    "id": f"topic-{i}",
                    "name": hashtag_name,
                    "category": "Campaign-Specific"
                })
        if campaign and campaign.keywords:
            campaign_keywords = campaign.keywords.split(",") if isinstance(campaign.keywords, str) else campaign.keywords
            for i, keyword in enumerate(campaign_keywords[:10]):
                keyword_clean = keyword.strip()
                if keyword_clean:
                    hashtag_name = f"#{keyword_clean.replace(' ', '')}"
                    hashtags.append({
                        "id": f"keyword-{i}",
                        "name": hashtag_name,
                        "category": "Industry"
                    })
        
        # Save to database cache (as "raw data" associated with campaign)
        # Only save if we have valid non-empty data
        if word_cloud and len(word_cloud) > 0 and topics and len(topics) > 0:
            try:
                import json
                research_data_record = db.query(CampaignResearchData).filter(
                    CampaignResearchData.campaign_id == campaign_id
                ).first()
                
                if research_data_record:
                    # Update existing record
                    research_data_record.word_cloud_json = json.dumps(word_cloud)
                    research_data_record.topics_json = json.dumps(topics)
                    research_data_record.hashtags_json = json.dumps(hashtags)
                    research_data_record.entities_json = json.dumps(entities)
                    research_data_record.updated_at = datetime.now()
                    logger.info(f"✅ Updated cached research data for campaign {campaign_id}")
                else:
                    # Create new record
                    research_data_record = CampaignResearchData(
                        campaign_id=campaign_id,
                        word_cloud_json=json.dumps(word_cloud),
                        topics_json=json.dumps(topics),
                        hashtags_json=json.dumps(hashtags),
                        entities_json=json.dumps(entities)
                    )
                    db.add(research_data_record)
                    logger.info(f"✅ Saved new research data to database for campaign {campaign_id}")
                
                db.commit()
            except Exception as e:
                logger.error(f"⚠️ Failed to save research data to database: {e}")
                db.rollback()
                # Continue anyway - return the data even if DB save failed
        else:
            logger.warning(f"⚠️ Not saving to cache - data is empty (wordCloud: {len(word_cloud) if word_cloud else 0}, topics: {len(topics) if topics else 0})")

        return {
            "status": "success",
            "campaign_id": campaign_id,
            "urls": urls,
            "raw": texts[: max(0, limit) or 20],
            "wordCloud": word_cloud,
            "topics": topics,
            "hashtags": hashtags,
            "entities": entities,
            "total_raw": len(texts),
            "truncation_info": truncation_info if truncation_info else None,  # Info about truncated texts
            "cached": False,
            "diagnostics": {
                "total_rows": len(rows),
                "valid_urls": len(urls),
                "valid_texts": len(texts),
                "errors": errors,
                "has_errors": len(errors) > 0,
                "has_data": len(urls) > 0 or len(texts) > 0,
                "truncated_count": len(truncation_info),
                "cached": False
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"Error aggregating research for {campaign_id}: {e}")
        logger.debug(traceback.format_exc())
        # Return partial data even if processing fails
        return {
            "urls": [],
            "raw": [],
            "wordCloud": [],
            "topics": [],
            "entities": {
                "persons": [],
                "organizations": [],
                "locations": [],
                "dates": [],
                "money": [],
                "percent": [],
                "time": [],
                "facility": []
            },
            "diagnostics": {
                "total_rows": 0,
                "valid_urls": 0,
                "valid_texts": 0,
                "errors": [{
                    "type": "processing_error",
                    "message": str(e),
                    "meta": {"traceback": traceback.format_exc()}
                }],
                "has_errors": True,
                "has_data": False
            }
        }

# Compare topics endpoint: re-process raw data with alternative method
@campaigns_research_router.get("/campaigns/{campaign_id}/compare-topics")
def compare_topics(campaign_id: str, method: str = "system", current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Re-process raw scraped data with alternative topic extraction method.
    Returns topics in the same format as research endpoint.
    REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION
    """
    # Verify campaign ownership
    from models import Campaign
    campaign = db.query(Campaign).filter(
        Campaign.campaign_id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found or access denied"
        )
    
    try:
        from models import CampaignRawData, SystemSettings
        from text_processing import extract_topics
        
        # Get raw data
        rows = db.query(CampaignRawData).filter(CampaignRawData.campaign_id == campaign_id).all()
        texts = []
        
        for r in rows:
            if r.extracted_text and len(r.extracted_text.strip()) > 0:
                if not r.source_url or not r.source_url.startswith(("error:", "placeholder:")):
                    texts.append(r.extracted_text)
        
        if not texts:
            return {
                "status": "error",
                "message": "No raw data available for comparison"
            }
        
        # Campaign ownership already verified above
        # Get campaign info
        campaign_query = campaign.query if campaign else ""
        campaign_keywords = campaign.keywords.split(",") if campaign and campaign.keywords else []
        campaign_urls = campaign.urls.split(",") if campaign and campaign.urls else []
        
        # Determine topic_tool based on method parameter
        if method == "llm":
            # Check if OpenAI API key is available
            openai_key = get_openai_api_key(current_user=current_user, db=db)
            if not openai_key:
                return {
                    "status": "error",
                    "message": "LLM method requires OpenAI API key. Please set a global key in Admin Settings > System > Platform Keys, or add your personal key in Account Settings."
                }
            topic_tool = "llm"
        else:
            topic_tool = "system"
        
        num_topics = 10
        iterations = 25
        
        logger.info(f"🔄 Comparing topics with method={method}, tool={topic_tool}, texts={len(texts)}")
        
        topic_phrases = extract_topics(
            texts,
            topic_tool=topic_tool,
            num_topics=num_topics,
            iterations=iterations,
            query=campaign_query,
            keywords=campaign_keywords,
            urls=campaign_urls
        )
        
        # Format topics same as research endpoint
        if topic_phrases and len(topic_phrases) > 0:
            topics = [{"label": phrase, "score": len(topic_phrases) - i} for i, phrase in enumerate(topic_phrases[:10])]
        else:
            topics = []
        
        return {
            "status": "success",
            "topics": topics,
            "method": method
        }
        
    except Exception as e:
        logger.error(f"Error in compare-topics endpoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": str(e)
        }

# TopicWizard Visualization endpoint
@campaigns_research_router.get("/campaigns/{campaign_id}/topicwizard")
def get_topicwizard_visualization(
    campaign_id: str,
    request: Request,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Generate TopicWizard visualization for campaign topics.
    Returns HTML page with interactive TopicWizard interface.
    
    Note: TopicWizard may have compatibility issues with Python 3.12 and numba/llvmlite.
    If import fails, returns a fallback visualization using the topic model data.
    REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION
    
    Supports authentication via:
    - Authorization header (Bearer token) - preferred
    - Query parameter 'token' - for iframe requests
    """
    # Get token from header or query parameter (for iframe support)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
    elif not token:
        # Try to get from query parameter
        token = request.query_params.get("token")
    
    if not token:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content="<html><body><h1>Authentication Required</h1><p>Please provide a valid authentication token.</p></body></html>",
            status_code=401
        )
    
    # Verify token and get user
    try:
        from utils import verify_token
        from models import User
        payload = verify_token(token)
        user_id = payload.get("sub")
        if not user_id:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(
                content="<html><body><h1>Invalid Token</h1><p>Token is missing user ID.</p></body></html>",
                status_code=401
            )
        current_user = db.query(User).filter(User.id == int(user_id)).first()
        if not current_user:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(
                content="<html><body><h1>User Not Found</h1><p>User associated with token not found.</p></body></html>",
                status_code=401
            )
    except Exception as e:
        logger.error(f"Authentication error in topicwizard endpoint: {e}")
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content=f"<html><body><h1>Authentication Failed</h1><p>Invalid or expired token.</p></body></html>",
            status_code=401
        )
    
    # Verify campaign ownership
    from models import Campaign
    campaign = db.query(Campaign).filter(
        Campaign.campaign_id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content="<html><body><h1>Campaign not found or access denied</h1></body></html>", status_code=404)
    
    try:
        from models import CampaignRawData
        from sklearn.decomposition import NMF
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.pipeline import Pipeline
        from fastapi.responses import HTMLResponse
        
        # Try to import TopicWizard (may fail on Python 3.12 due to numba/llvmlite issues)
        try:
            import topicwizard
            TOPICWIZARD_AVAILABLE = True
        except (ImportError, AttributeError, Exception) as tw_err:
            logger.warning(f"⚠️ TopicWizard not available (known issue with Python 3.12/numba): {tw_err}")
            TOPICWIZARD_AVAILABLE = False
        
        # Campaign ownership already verified above
        # Get scraped texts
        rows = db.query(CampaignRawData).filter(CampaignRawData.campaign_id == campaign_id).all()
        texts = []
        for r in rows:
            if r.extracted_text and len(r.extracted_text.strip()) > 0 and not (r.source_url and r.source_url.startswith(("error:", "placeholder:"))):
                texts.append(r.extracted_text.strip())
        
        db_settings = SessionLocal()
        try:
                # Load system model settings
                tfidf_min_df = 3
                tfidf_max_df = 0.7
                num_topics = 10
                
                settings = db_settings.query(SystemSettings).filter(
                    SystemSettings.setting_key.like("system_model_%")
                ).all()
                
                for setting in settings:
                    key = setting.setting_key.replace("system_model_", "")
                    value = setting.setting_value
                    if key == "tfidf_min_df":
                        tfidf_min_df = int(value) if value else 3
                    elif key == "tfidf_max_df":
                        tfidf_max_df = float(value) if value else 0.7
                    elif key == "k_grid":
                        k_grid = json.loads(value) if value else [10, 15, 20, 25]
                        num_topics = k_grid[0] if k_grid else 10
                
                # Load visualizer settings
                max_texts = 100
                top_words_per_topic = 10
                grid_columns = 0  # 0 = auto-fill
                sort_order = "coverage"  # "coverage" or "topic_id"
                show_coverage = True
                show_top_weights = False
                visualization_type = "scatter"  # All types: "columns", "scatter", "bubble", "network", "word-cloud", "word_map", "topic_map", "document_map", "heatmap", "treemap"
                color_scheme = "rainbow"  # "single", "gradient", "rainbow", "categorical", "viridis", "plasma", "inferno"
                size_scaling = True
                show_title = False
                show_info_box = False
                background_color = "#ffffff"
                min_size = 20
                max_size = 100
                # Advanced styling
                opacity = 0.7
                font_size = 14
                font_weight = 600
                spacing = 20
                border_radius = 8
                border_width = 2
                border_color = "#333333"
                shadow_enabled = False
                # Layout
                orientation = "horizontal"
                alignment = "center"
                padding = 20
                margin = 10
                # Animation
                hover_effects = True
                animation_speed = 300
                # Visualization-specific
                word_map_layout = "force"
                word_map_link_distance = 50
                topic_map_clustering = True
                topic_map_distance = 100
                document_map_point_size = 5
                document_map_color_by = "topic"
                
                visualizer_settings = db_settings.query(SystemSettings).filter(
                    SystemSettings.setting_key.like("visualizer_%")
                ).all()
                
                logger.info(f"🔍 Found {len(visualizer_settings)} visualizer settings in database")
                if len(visualizer_settings) == 0:
                    logger.warning("⚠️ No visualizer settings found in database - using defaults!")
                for setting in visualizer_settings:
                    logger.info(f"  ✓ {setting.setting_key} = '{setting.setting_value}'")
                
                for setting in visualizer_settings:
                    key = setting.setting_key.replace("visualizer_", "")
                    value = setting.setting_value
                    if key == "max_documents":
                        max_texts = int(value) if value else 100
                    elif key == "top_words_per_topic":
                        top_words_per_topic = int(value) if value else 10
                    elif key == "grid_columns":
                        grid_columns = int(value) if value else 0
                    elif key == "sort_order":
                        sort_order = value if value in ["coverage", "topic_id"] else "coverage"
                    elif key == "show_coverage":
                        show_coverage = value.lower() == "true" if value else True
                    elif key == "show_top_weights":
                        show_top_weights = value.lower() == "true" if value else False
                    elif key == "visualization_type":
                        valid_types = ["columns", "scatter", "bubble", "network", "word-cloud", "word_map", "topic_map", "document_map", "heatmap", "treemap"]
                        visualization_type = value if value in valid_types else "scatter"
                        logger.info(f"📊 Loaded visualization_type: {visualization_type} (raw DB value: '{value}')")
                    elif key == "color_scheme":
                        valid_schemes = ["single", "gradient", "rainbow", "categorical", "viridis", "plasma", "inferno"]
                        color_scheme = value if value in valid_schemes else "rainbow"
                    elif key == "size_scaling":
                        size_scaling = value.lower() == "true" if value else True
                    elif key == "show_title":
                        show_title = value.lower() == "true" if value else False
                    elif key == "show_info_box":
                        show_info_box = value.lower() == "true" if value else False
                    elif key == "background_color":
                        background_color = value if value else "#ffffff"
                    elif key == "min_size":
                        min_size = int(value) if value else 20
                    elif key == "max_size":
                        max_size = int(value) if value else 100
                    # Advanced styling
                    elif key == "opacity":
                        opacity = float(value) if value else 0.7
                    elif key == "font_size":
                        font_size = int(value) if value else 14
                    elif key == "font_weight":
                        font_weight = int(value) if value else 600
                    elif key == "spacing":
                        spacing = int(value) if value else 20
                    elif key == "border_radius":
                        border_radius = int(value) if value else 8
                    elif key == "border_width":
                        border_width = int(value) if value else 2
                    elif key == "border_color":
                        border_color = value if value else "#333333"
                    elif key == "shadow_enabled":
                        shadow_enabled = value.lower() == "true" if value else False
                    # Layout
                    elif key == "orientation":
                        orientation = value if value in ["horizontal", "vertical"] else "horizontal"
                    elif key == "alignment":
                        alignment = value if value in ["left", "center", "right"] else "center"
                    elif key == "padding":
                        padding = int(value) if value else 20
                    elif key == "margin":
                        margin = int(value) if value else 10
                    # Animation
                    elif key == "hover_effects":
                        hover_effects = value.lower() == "true" if value else True
                    elif key == "animation_speed":
                        animation_speed = int(value) if value else 300
                    # Visualization-specific
                    elif key == "word_map_layout":
                        word_map_layout = value if value in ["force", "circular", "hierarchical"] else "force"
                    elif key == "word_map_link_distance":
                        word_map_link_distance = int(value) if value else 50
                    elif key == "topic_map_clustering":
                        topic_map_clustering = value.lower() == "true" if value else True
                    elif key == "topic_map_distance":
                        topic_map_distance = int(value) if value else 100
                    elif key == "document_map_point_size":
                        document_map_point_size = int(value) if value else 5
                    elif key == "document_map_color_by":
                        document_map_color_by = value if value in ["topic", "coverage", "document"] else "topic"
            finally:
                db_settings.close()
        except Exception as e:
            logger.warning(f"Could not load settings, using defaults: {e}")
            tfidf_min_df = 3
            tfidf_max_df = 0.7
            num_topics = 10
            max_texts = 100
            top_words_per_topic = 10
            grid_columns = 0
            sort_order = "coverage"
            show_coverage = True
            show_top_weights = False
            visualization_type = "scatter"
            color_scheme = "rainbow"
            size_scaling = True
            show_title = False
            show_info_box = False
            background_color = "#ffffff"
            min_size = 20
            max_size = 100
        
        # Limit texts for performance (TopicWizard can be slow with many documents)
        if len(texts) > max_texts:
            texts = texts[:max_texts]
            logger.info(f"Limited to {max_texts} texts for TopicWizard performance")
        
        # Create pipeline compatible with TopicWizard
        vectorizer = TfidfVectorizer(
            min_df=tfidf_min_df,
            max_df=tfidf_max_df,
            stop_words='english',
            strip_accents='unicode'
        )
        
        topic_model = NMF(
            n_components=min(num_topics, len(texts) - 1),
            random_state=42,
            max_iter=500
        )
        
        topic_pipeline = Pipeline([
            ("vectorizer", vectorizer),
            ("topic_model", topic_model),
        ])
        
        # Fit the pipeline
        logger.info(f"Fitting topic model pipeline with {len(texts)} documents, {min(num_topics, len(texts) - 1)} topics")
        try:
            topic_pipeline.fit(texts)
        except ValueError as e:
            if "no terms remain" in str(e).lower() or "after pruning" in str(e).lower():
                logger.warning(f"⚠️ TopicWizard: No terms remain after pruning. Adjusting min_df/max_df parameters.")
                # Try with more lenient parameters
                vectorizer = TfidfVectorizer(
                    min_df=1,  # Allow terms that appear in at least 1 document
                    max_df=0.95,  # Allow terms that appear in up to 95% of documents
                    stop_words='english',
                    strip_accents='unicode'
                )
                topic_model = NMF(
                    n_components=min(num_topics, len(texts) - 1),
                    random_state=42,
                    max_iter=500
                )
                topic_pipeline = Pipeline([
                    ("vectorizer", vectorizer),
                    ("topic_model", topic_model),
                ])
                try:
                    topic_pipeline.fit(texts)
                    logger.info("✅ TopicWizard: Successfully fitted with adjusted parameters")
                except Exception as e2:
                    logger.error(f"❌ TopicWizard: Still failed after parameter adjustment: {e2}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"TopicWizard failed: {str(e2)}. Try reducing min_df or increasing max_df, or ensure you have sufficient text data."
                    )
            else:
                raise
        
        # Extract topic information for visualization
        vectorizer = topic_pipeline.named_steps['vectorizer']
        nmf_model = topic_pipeline.named_steps['topic_model']
        
        # Get document-topic matrix
        X = vectorizer.transform(texts)
        doc_topic_matrix = nmf_model.transform(X)
        
        # Get topic-word matrix and top words per topic
        topic_word_matrix = nmf_model.components_
        feature_names = vectorizer.get_feature_names_out()
        
        topics_data = []
        for topic_idx in range(min(num_topics, len(texts) - 1)):
            # Get top N words for this topic (using visualizer setting)
            top_word_indices = topic_word_matrix[topic_idx].argsort()[-top_words_per_topic:][::-1]
            top_words = [feature_names[idx] for idx in top_word_indices]
            top_weights = [topic_word_matrix[topic_idx][idx] for idx in top_word_indices]
            
            # Calculate topic strength (document coverage)
            topic_strength = doc_topic_matrix[:, topic_idx].sum()
            coverage_pct = (topic_strength / doc_topic_matrix.sum()) * 100 if doc_topic_matrix.sum() > 0 else 0
            
            topics_data.append({
                'id': topic_idx,
                'top_words': top_words,
                'top_weights': top_weights,
                'coverage': round(coverage_pct, 1)
            })
        
        # Sort by configured order
        if sort_order == "coverage":
            topics_data.sort(key=lambda x: x['coverage'], reverse=True)
        else:  # topic_id
            topics_data.sort(key=lambda x: x['id'])
        
        # Helper function to get color for a topic based on scheme
        def get_topic_color(topic_idx, total_topics, coverage):
            ratio = topic_idx / max(total_topics, 1)
            if color_scheme == "rainbow":
                # Rainbow: hue from 0 to 360
                hue = ratio * 360
                return f"hsl({hue}, 70%, 60%)"
            elif color_scheme == "gradient":
                # Gradient: blue to purple
                r = int(59 + (147 - 59) * ratio)
                g = int(130 + (112 - 130) * ratio)
                b = int(246 + (219 - 246) * ratio)
                return f"rgb({r}, {g}, {b})"
            elif color_scheme == "categorical":
                # Categorical: distinct colors
                colors = ["#3b82f6", "#22c55e", "#a855f7", "#eab308", "#ef4444", "#64748b", "#f97316", "#06b6d4", "#8b5cf6", "#ec4899"]
                return colors[topic_idx % len(colors)]
            elif color_scheme == "viridis":
                # Viridis: yellow-green-blue (scientific colormap)
                if ratio < 0.25:
                    r, g, b = int(68 + (72 - 68) * (ratio / 0.25)), int(1 + (40 - 1) * (ratio / 0.25)), int(84 + (54 - 84) * (ratio / 0.25))
                elif ratio < 0.5:
                    r, g, b = int(72 + (33 - 72) * ((ratio - 0.25) / 0.25)), int(40 + (144 - 40) * ((ratio - 0.25) / 0.25)), int(54 + (140 - 54) * ((ratio - 0.25) / 0.25))
                elif ratio < 0.75:
                    r, g, b = int(33 + (28 - 33) * ((ratio - 0.5) / 0.25)), int(144 + (127 - 144) * ((ratio - 0.5) / 0.25)), int(140 + (135 - 140) * ((ratio - 0.5) / 0.25))
                else:
                    r, g, b = int(28 + (253 - 28) * ((ratio - 0.75) / 0.25)), int(127 + (231 - 127) * ((ratio - 0.75) / 0.25)), int(135 + (37 - 135) * ((ratio - 0.75) / 0.25))
                return f"rgb({r}, {g}, {b})"
            elif color_scheme == "plasma":
                # Plasma: purple-pink-yellow (high contrast)
                if ratio < 0.33:
                    r, g, b = int(13 + (75 - 13) * (ratio / 0.33)), int(8 + (10 - 8) * (ratio / 0.33)), int(135 + (130 - 135) * (ratio / 0.33))
                elif ratio < 0.66:
                    r, g, b = int(75 + (190 - 75) * ((ratio - 0.33) / 0.33)), int(10 + (40 - 10) * ((ratio - 0.33) / 0.33)), int(130 + (50 - 130) * ((ratio - 0.33) / 0.33))
                else:
                    r, g, b = int(190 + (253 - 190) * ((ratio - 0.66) / 0.34)), int(40 + (231 - 40) * ((ratio - 0.66) / 0.34)), int(50 + (37 - 50) * ((ratio - 0.66) / 0.34))
                return f"rgb({r}, {g}, {b})"
            elif color_scheme == "inferno":
                # Inferno: black-red-yellow (dark theme)
                if ratio < 0.33:
                    r, g, b = int(0 + (20 - 0) * (ratio / 0.33)), int(0 + (11 - 0) * (ratio / 0.33)), int(4 + (52 - 4) * (ratio / 0.33))
                elif ratio < 0.66:
                    r, g, b = int(20 + (153 - 20) * ((ratio - 0.33) / 0.33)), int(11 + (52 - 11) * ((ratio - 0.33) / 0.33)), int(52 + (4 - 52) * ((ratio - 0.33) / 0.33))
                else:
                    r, g, b = int(153 + (252 - 153) * ((ratio - 0.66) / 0.34)), int(52 + (141 - 52) * ((ratio - 0.66) / 0.34)), int(4 + (89 - 4) * ((ratio - 0.66) / 0.34))
                return f"rgb({r}, {g}, {b})"
            else:  # single
                # Single: monochromatic with variations
                base = 61  # #3d545f
                variation = (topic_idx % 5) * 20
                return f"rgb({base + variation}, {84 + variation}, {95 + variation})"
        
        # Helper function to calculate size based on coverage
        def get_topic_size(coverage, max_coverage):
            if not size_scaling:
                return (min_size + max_size) / 2
            if max_coverage == 0:
                return min_size
            ratio = coverage / max_coverage
            return min_size + (max_size - min_size) * ratio
        
        # Calculate max coverage for size scaling
        max_coverage = max([t['coverage'] for t in topics_data]) if topics_data else 100
        
        # Generate visualization based on type
        logger.info(f"🎨 Generating {visualization_type} visualization with {len(topics_data)} topics")
        logger.info(f"   Basic Settings: color_scheme={color_scheme}, size_scaling={size_scaling}, show_title={show_title}, show_info_box={show_info_box}")
        logger.info(f"   Styling: opacity={opacity}, font_size={font_size}, font_weight={font_weight}, border_radius={border_radius}, border_width={border_width}")
        logger.info(f"   Layout: orientation={orientation}, alignment={alignment}, padding={padding}, margin={margin}, spacing={spacing}")
        logger.info(f"   Animation: hover_effects={hover_effects}, animation_speed={animation_speed}, shadow_enabled={shadow_enabled}")
        logger.info(f"   Background: {background_color}, min_size={min_size}, max_size={max_size}")
        topics_html = ""
        total_topics = len(topics_data)
        
        if visualization_type == "scatter" or visualization_type == "bubble":
            # Scatter/Bubble plot with SVG
            svg_width = 1000
            svg_height = 600
            shadow_style = f"filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.2));" if shadow_enabled else ""
            topics_html = f'<svg width="{svg_width}" height="{svg_height}" style="background: {background_color}; border-radius: {border_radius}px; padding: {padding}px; margin: {margin}px; {shadow_style}">'
            
            for i, topic in enumerate(topics_data):
                # Calculate position (scattered)
                angle = (i / total_topics) * 2 * 3.14159
                radius = 150 + (i % 3) * 50
                x = svg_width / 2 + radius * (0.7 if i % 2 == 0 else -0.7) * (i / total_topics)
                y = svg_height / 2 + radius * (0.5 if i % 3 == 0 else -0.5) * ((i * 1.3) / total_topics)
                
                # Ensure within bounds
                x = max(50, min(svg_width - 50, x))
                y = max(50, min(svg_height - 50, y))
                
                size = get_topic_size(topic['coverage'], max_coverage)
                color = get_topic_color(i, total_topics, topic['coverage'])
                
                # Draw circle/bubble with loaded settings
                topics_html += f'<circle cx="{x}" cy="{y}" r="{size/2}" fill="{color}" opacity="{opacity}" stroke="{border_color}" stroke-width="{border_width}"/>'
                
                # Add label with loaded font settings
                label_text = ", ".join(topic['top_words'][:3])
                if show_coverage:
                    label_text += f" ({topic['coverage']}%)"
                topics_html += f'<text x="{x}" y="{y + size/2 + 15}" text-anchor="middle" font-size="{font_size}" fill="#333" font-weight="{font_weight}">{label_text}</text>'
            
            topics_html += '</svg>'
            
        elif visualization_type == "network":
            # Network graph
            svg_width = 1000
            svg_height = 600
            shadow_style = f"filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.2));" if shadow_enabled else ""
            topics_html = f'<svg width="{svg_width}" height="{svg_height}" style="background: {background_color}; border-radius: {border_radius}px; padding: {padding}px; margin: {margin}px; {shadow_style}">'
            
            # Position topics in a circle
            center_x, center_y = svg_width / 2, svg_height / 2
            radius = 200
            
            for i, topic in enumerate(topics_data):
                angle = (i / total_topics) * 2 * 3.14159
                x = center_x + radius * (1 + (i % 3) * 0.3) * (0.8 if i % 2 == 0 else 1.2) * (i / total_topics)
                y = center_y + radius * (1 + (i % 3) * 0.3) * (0.8 if i % 2 == 0 else 1.2) * ((i * 1.5) / total_topics)
                
                x = max(60, min(svg_width - 60, x))
                y = max(60, min(svg_height - 60, y))
                
                size = get_topic_size(topic['coverage'], max_coverage)
                color = get_topic_color(i, total_topics, topic['coverage'])
                
                # Draw connections to nearby topics
                if i < total_topics - 1:
                    next_topic = topics_data[(i + 1) % total_topics]
                    next_angle = ((i + 1) / total_topics) * 2 * 3.14159
                    next_x = center_x + radius * (1 + ((i + 1) % 3) * 0.3) * (0.8 if (i + 1) % 2 == 0 else 1.2) * ((i + 1) / total_topics)
                    next_y = center_y + radius * (1 + ((i + 1) % 3) * 0.3) * (0.8 if (i + 1) % 2 == 0 else 1.2) * (((i + 1) * 1.5) / total_topics)
                    next_x = max(60, min(svg_width - 60, next_x))
                    next_y = max(60, min(svg_height - 60, next_y))
                    topics_html += f'<line x1="{x}" y1="{y}" x2="{next_x}" y2="{next_y}" stroke="#ccc" stroke-width="1" opacity="{opacity * 0.5}"/>'
                
                # Draw node with loaded settings
                topics_html += f'<circle cx="{x}" cy="{y}" r="{size/2}" fill="{color}" opacity="{opacity}" stroke="{border_color}" stroke-width="{border_width}"/>'
                
                # Add label with loaded font settings
                label_text = ", ".join(topic['top_words'][:2])
                topics_html += f'<text x="{x}" y="{y + size/2 + 12}" text-anchor="middle" font-size="{font_size}" fill="#333" font-weight="{font_weight}">{label_text}</text>'
            
            topics_html += '</svg>'
            
        elif visualization_type == "word-cloud":
            # Word cloud style
            shadow_style = f"text-shadow: 2px 2px 4px rgba(0,0,0,0.2);" if shadow_enabled else ""
            topics_html = f'<div class="word-cloud" style="padding: {padding}px; margin: {margin}px;">'
            for i, topic in enumerate(topics_data):
                size = get_topic_size(topic['coverage'], max_coverage)
                color = get_topic_color(i, total_topics, topic['coverage'])
                words = ", ".join(topic['top_words'][:5])
                cloud_font_size = max(font_size, min(font_size + 10, size / 4))
                topics_html += f'<span class="cloud-word" style="font-size: {cloud_font_size}px; font-weight: {font_weight}; color: {color}; margin: {spacing/4}px; opacity: {opacity}; {shadow_style}">{words}</span>'
            topics_html += '</div>'
            
        elif visualization_type == "word_map":
            # Word map: shows relationships between words
            svg_width = 1000
            svg_height = 600
            shadow_style = f"filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.2));" if shadow_enabled else ""
            topics_html = f'<svg width="{svg_width}" height="{svg_height}" style="background: {background_color}; border-radius: {border_radius}px; padding: {padding}px; margin: {margin}px; {shadow_style}">'
            # Place words in a force-directed layout
            for i, topic in enumerate(topics_data):
                angle = (i / total_topics) * 2 * 3.14159
                x = svg_width / 2 + 200 * (0.8 if i % 2 == 0 else 1.2) * (i / total_topics)
                y = svg_height / 2 + 200 * (0.8 if i % 3 == 0 else 1.2) * ((i * 1.3) / total_topics)
                x = max(50, min(svg_width - 50, x))
                y = max(50, min(svg_height - 50, y))
                color = get_topic_color(i, total_topics, topic['coverage'])
                # Draw word nodes with loaded settings
                for j, word in enumerate(topic['top_words'][:3]):
                    word_x = x + (j - 1) * word_map_link_distance
                    word_y = y + (j % 2) * spacing
                    topics_html += f'<circle cx="{word_x}" cy="{word_y}" r="15" fill="{color}" opacity="{opacity}" stroke="{border_color}" stroke-width="{border_width}"/>'
                    topics_html += f'<text x="{word_x}" y="{word_y + 5}" text-anchor="middle" font-size="{font_size}" fill="#333" font-weight="{font_weight}">{word}</text>'
            topics_html += '</svg>'
            
        elif visualization_type == "topic_map":
            # Topic map: shows topic similarity/clustering
            svg_width = 1000
            svg_height = 600
            shadow_style = f"filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.2));" if shadow_enabled else ""
            topics_html = f'<svg width="{svg_width}" height="{svg_height}" style="background: {background_color}; border-radius: {border_radius}px; padding: {padding}px; margin: {margin}px; {shadow_style}">'
            center_x, center_y = svg_width / 2, svg_height / 2
            for i, topic in enumerate(topics_data):
                angle = (i / total_topics) * 2 * 3.14159
                distance = topic_map_distance if topic_map_clustering else 150
                x = center_x + distance * (1 + (i % 3) * 0.2) * (0.9 if i % 2 == 0 else 1.1) * (i / total_topics)
                y = center_y + distance * (1 + (i % 3) * 0.2) * (0.9 if i % 2 == 0 else 1.1) * ((i * 1.4) / total_topics)
                x = max(60, min(svg_width - 60, x))
                y = max(60, min(svg_height - 60, y))
                size = get_topic_size(topic['coverage'], max_coverage)
                color = get_topic_color(i, total_topics, topic['coverage'])
                topics_html += f'<circle cx="{x}" cy="{y}" r="{size/2}" fill="{color}" opacity="{opacity}" stroke="{border_color}" stroke-width="{border_width}"/>'
                label_text = ", ".join(topic['top_words'][:2])
                topics_html += f'<text x="{x}" y="{y + size/2 + 15}" text-anchor="middle" font-size="{font_size}" fill="#333" font-weight="{font_weight}">{label_text}</text>'
            topics_html += '</svg>'
            
        elif visualization_type == "document_map":
            # Document map: shows document clustering
            svg_width = 1000
            svg_height = 600
            shadow_style = f"filter: drop-shadow(1px 1px 2px rgba(0,0,0,0.1));" if shadow_enabled else ""
            topics_html = f'<svg width="{svg_width}" height="{svg_height}" style="background: {background_color}; border-radius: {border_radius}px; padding: {padding}px; margin: {margin}px; {shadow_style}">'
            # Represent documents as points colored by topic
            for i, topic in enumerate(topics_data):
                color = get_topic_color(i, total_topics, topic['coverage'])
                # Place multiple points per topic to represent documents
                num_points = max(3, int(topic['coverage'] / 10))
                for j in range(num_points):
                    angle = (i / total_topics + j / num_points) * 2 * 3.14159
                    x = svg_width / 2 + 150 * (1 + j * 0.1) * (0.8 if i % 2 == 0 else 1.2) * (i / total_topics)
                    y = svg_height / 2 + 150 * (1 + j * 0.1) * (0.8 if i % 3 == 0 else 1.2) * ((i * 1.3) / total_topics)
                    x = max(20, min(svg_width - 20, x))
                    y = max(20, min(svg_height - 20, y))
                    topics_html += f'<circle cx="{x}" cy="{y}" r="{document_map_point_size}" fill="{color}" opacity="{opacity}"/>'
            topics_html += '</svg>'
            
        elif visualization_type == "heatmap":
            # Heatmap: topic-document matrix
            topics_html = '<div class="heatmap-container">'
            topics_html += '<table class="heatmap-table">'
            # Header row
            topics_html += '<tr><th>Topic</th>'
            for i in range(min(10, len(texts))):
                topics_html += f'<th>Doc {i+1}</th>'
            topics_html += '</tr>'
            # Data rows
            for i, topic in enumerate(topics_data):
                color = get_topic_color(i, total_topics, topic['coverage'])
                topics_html += f'<tr><td style="font-weight: {font_weight};">Topic {i+1}</td>'
                for j in range(min(10, len(texts))):
                    intensity = (i + j) % 10 / 10  # Simplified intensity
                    bg_color = color.replace('rgb', 'rgba').replace(')', f', {intensity})')
                    topics_html += f'<td style="background: {bg_color}; padding: 5px;"></td>'
                topics_html += '</tr>'
            topics_html += '</table></div>'
            
        elif visualization_type == "treemap":
            # Treemap: hierarchical coverage visualization
            svg_width = 1000
            svg_height = 600
            shadow_style = f"filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.2));" if shadow_enabled else ""
            topics_html = f'<svg width="{svg_width}" height="{svg_height}" style="background: {background_color}; border-radius: {border_radius}px; padding: {padding}px; margin: {margin}px; {shadow_style}">'
            # Calculate total coverage for sizing
            total_coverage = sum(t['coverage'] for t in topics_data)
            current_x, current_y = padding, padding
            row_height = (svg_height - padding * 2) / max(3, int(len(topics_data) ** 0.5))
            for i, topic in enumerate(topics_data):
                width = (topic['coverage'] / total_coverage) * (svg_width - padding * 2) if total_coverage > 0 else (svg_width - padding * 2) / len(topics_data)
                if current_x + width > svg_width - padding:
                    current_x = padding
                    current_y += row_height
                color = get_topic_color(i, total_topics, topic['coverage'])
                topics_html += f'<rect x="{current_x}" y="{current_y}" width="{width}" height="{row_height}" fill="{color}" opacity="{opacity}" stroke="{border_color}" stroke-width="{border_width}"/>'
                label_text = ", ".join(topic['top_words'][:2])
                topics_html += f'<text x="{current_x + width/2}" y="{current_y + row_height/2}" text-anchor="middle" font-size="{font_size}" fill="#333" font-weight="{font_weight}">{label_text}</text>'
                current_x += width
            topics_html += '</svg>'
            
        else:  # columns (default)
            # Column cards (grid layout)
            shadow_style = f"box-shadow: 2px 2px 4px rgba(0,0,0,0.2);" if shadow_enabled else ""
            for i, topic in enumerate(topics_data):
                words_display = []
                for j, word in enumerate(topic['top_words']):
                    word_html = f"<strong>{word}</strong>" if j < 3 else word
                    if show_top_weights and j < len(topic['top_weights']):
                        weight = round(topic['top_weights'][j], 3)
                        word_html += f" <span class='weight'>({weight})</span>"
                    words_display.append(word_html)
                words_html = ", ".join(words_display)
                
                title = f"Topic {topic['id'] + 1}"
                if show_coverage:
                    title += f" ({topic['coverage']}% coverage)"
                
                color = get_topic_color(i, total_topics, topic['coverage'])
                
                topics_html += f"""
                <div class="topic-card" style="border-left-color: {color}; border-left-width: {border_width}px; border-radius: {border_radius}px; padding: {padding}px; margin: {margin}px; opacity: {opacity}; {shadow_style}">
                    <h3 style="font-size: {font_size + 2}px; font-weight: {font_weight};">{title}</h3>
                    <p class="topic-words" style="font-size: {font_size}px; font-weight: {font_weight - 200 if font_weight > 400 else 400};">{words_html}</p>
                </div>
                """
        
        # Determine container class based on visualization type
        container_class = "topics-grid" if visualization_type == "columns" else "visualization-container"
        
        # Build alignment style
        align_style = f"text-align: {alignment};" if alignment in ["left", "center", "right"] else "text-align: center;"
        
        # Build orientation style
        flex_direction = "row" if orientation == "horizontal" else "column"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Topic Visualization - Campaign {campaign_id}</title>
    <meta charset="utf-8">
    <style>
        body {{
            margin: 0;
            padding: {padding}px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: {background_color};
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: {background_color};
            padding: {padding}px;
            border-radius: {border_radius}px;
            {align_style}
        }}
        h1 {{
            color: #333;
            margin-bottom: 20px;
        }}
        .info {{
            background: #e3f2fd;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }}
        .info p {{
            margin: 5px 0;
        }}
        .topics-grid {{
            display: grid;
            grid-template-columns: {"repeat(" + str(grid_columns) + ", 1fr)" if grid_columns > 0 else "repeat(auto-fill, minmax(300px, 1fr))"};
            gap: {spacing}px;
            margin-top: {margin}px;
            flex-direction: {flex_direction};
        }}
        .visualization-container {{
            width: 100%;
            display: flex;
            flex-direction: {flex_direction};
            justify-content: {"flex-start" if alignment == "left" else "flex-end" if alignment == "right" else "center"};
            align-items: center;
            margin-top: {margin}px;
            padding: {padding}px;
        }}
        .topic-card {{
            background: #f8f9fa;
            padding: {padding}px;
            border-radius: {border_radius}px;
            border-left: {border_width}px solid #3d545f;
            transition: transform {animation_speed}ms ease{" " if hover_effects else ""};
        }}
        {"        .topic-card:hover { transform: scale(1.02); }" if hover_effects else ""}
        .topic-card h3 {{
            margin: 0 0 {spacing/2}px 0;
            color: #3d545f;
            font-size: {font_size + 2}px;
            font-weight: {font_weight};
        }}
        .topic-words {{
            margin: 0;
            color: #666;
            font-size: {font_size}px;
            font-weight: {font_weight - 200 if font_weight > 400 else 400};
            line-height: 1.6;
        }}
        .topic-words strong {{
            color: #3d545f;
            font-weight: 600;
        }}
        .topic-words .weight {{
            color: #999;
            font-size: 12px;
            font-weight: normal;
        }}
        .word-cloud {{
            display: flex;
            flex-wrap: wrap;
            justify-content: {"flex-start" if alignment == "left" else "flex-end" if alignment == "right" else "center"};
            align-items: center;
            padding: {padding}px;
            min-height: 400px;
            flex-direction: {flex_direction};
        }}
        .cloud-word {{
            display: inline-block;
            padding: {spacing/4}px {spacing/2}px;
            border-radius: {border_radius}px;
            font-weight: {font_weight};
            transition: transform {animation_speed}ms ease{" " if hover_effects else ""};
        }}
        {"        .cloud-word:hover { transform: scale(1.1); }" if hover_effects else ""}
        .heatmap-container {{
            padding: {padding}px;
            margin: {margin}px;
        }}
        .heatmap-table {{
            width: 100%;
            border-collapse: collapse;
            border-radius: {border_radius}px;
            overflow: hidden;
        }}
        .heatmap-table th, .heatmap-table td {{
            padding: {spacing/2}px;
            border: {border_width}px solid {border_color};
            text-align: center;
            font-size: {font_size}px;
        }}
        .note {{
            background: #fff3cd;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
            font-size: 14px;
        }}
        .warning {{
            background: #f8d7da;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
            font-size: 14px;
            color: #721c24;
        }}
    </style>
</head>
<body>
    <div class="container">
        {"<h1>Topic Model Visualization</h1>" if show_title else ""}
        {"<div class='info'><p><strong>Campaign ID:</strong> {campaign_id}</p><p><strong>Documents:</strong> {len(texts)}</p><p><strong>Topics:</strong> {min(num_topics, len(texts) - 1)}</p></div>" if show_info_box else ""}
        {"<div class='warning'><strong>Note:</strong> TopicWizard interactive visualization is not available due to Python 3.12 compatibility issues with numba/llvmlite. Showing topic model results instead.</div>" if not TOPICWIZARD_AVAILABLE else ""}
        <div class="{container_class}">
            {topics_html}
        </div>
    </div>
</body>
</html>
"""
        
        response = HTMLResponse(content=html_content)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
        
    except ImportError as e:
        logger.error(f"Required packages not available: {e}")
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>Required packages not available: {str(e)}</p><p>Please install: pip install scikit-learn topic-wizard</p></body></html>",
            status_code=503
        )
    except Exception as e:
        logger.error(f"Error generating TopicWizard visualization: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>{str(e)}</p><p>Check backend logs for details.</p></body></html>",
            status_code=500
        )

# Knowledge Graph Visualization endpoint
@campaigns_research_router.get("/campaigns/{campaign_id}/knowledge-graph")
def get_knowledge_graph_visualization(
    campaign_id: str, 
    request: Request,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Generate knowledge graph visualization for campaign using NetworkX and pyvis.
    Uses existing extracted data: entities, topics, and word cloud from /research endpoint.
    Returns HTML page with interactive knowledge graph.
    REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION
    
    Supports authentication via:
    - Authorization header (Bearer token) - preferred
    - Query parameter 'token' - for iframe requests
    """
    # Get token from header or query parameter (for iframe support)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
    elif not token:
        # Try to get from query parameter
        token = request.query_params.get("token")
    
    if not token:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content="<html><body><h1>Authentication Required</h1><p>Please provide a valid authentication token.</p></body></html>",
            status_code=401
        )
    
    # Verify token and get user
    try:
        from utils import verify_token
        from models import User
        payload = verify_token(token)
        user_id = payload.get("sub")
        if not user_id:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(
                content="<html><body><h1>Invalid Token</h1><p>Token is missing user ID.</p></body></html>",
                status_code=401
            )
        current_user = db.query(User).filter(User.id == int(user_id)).first()
        if not current_user:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(
                content="<html><body><h1>User Not Found</h1><p>User associated with token not found.</p></body></html>",
                status_code=401
            )
    except Exception as e:
        logger.error(f"Authentication error in knowledge graph endpoint: {e}")
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content=f"<html><body><h1>Authentication Failed</h1><p>Invalid or expired token.</p></body></html>",
            status_code=401
        )
    
    # Verify campaign ownership
    from models import Campaign
    campaign = db.query(Campaign).filter(
        Campaign.campaign_id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content="<html><body><h1>Campaign not found or access denied</h1></body></html>", status_code=404)
    
    try:
        from models import CampaignRawData, CampaignResearchData, SystemSettings
        from fastapi.responses import HTMLResponse
        import json
        import networkx as nx
        from pyvis.network import Network
        
        # Get research data (entities, topics, word cloud) - use cached if available
        cached_data = db.query(CampaignResearchData).filter(
            CampaignResearchData.campaign_id == campaign_id
        ).first()
        
        # Get raw texts for relationship extraction
        rows = db.query(CampaignRawData).filter(CampaignRawData.campaign_id == campaign_id).all()
        texts = []
        for r in rows:
            if r.extracted_text and len(r.extracted_text.strip()) > 0 and not (r.source_url and r.source_url.startswith(("error:", "placeholder:"))):
                texts.append(r.extracted_text.strip())
        
        if len(texts) < 1:
            return HTMLResponse(
                content="<html><body><h1>Insufficient Data</h1><p>Need at least 1 document for knowledge graph. Please scrape content first.</p></body></html>",
                status_code=400
            )
        
        # Load entities, topics, word cloud from cache or extract
        if cached_data and cached_data.entities_json and cached_data.topics_json and cached_data.word_cloud_json:
            try:
                entities = json.loads(cached_data.entities_json) if cached_data.entities_json else {}
                topics = json.loads(cached_data.topics_json) if cached_data.topics_json else []
                word_cloud = json.loads(cached_data.word_cloud_json) if cached_data.word_cloud_json else []
            except json.JSONDecodeError:
                entities = {}
                topics = []
                word_cloud = []
        else:
            # Fallback: minimal data
            entities = {
                "persons": [],
                "organizations": [],
                "locations": [],
                "dates": [],
                "money": [],
                "percent": [],
                "time": [],
                "facility": []
            }
            topics = []
            word_cloud = []
        
        # Load knowledge graph settings from database
        kg_settings = {}
        settings = db.query(SystemSettings).filter(
            SystemSettings.setting_key.like("knowledge_graph_%")
        ).all()
        
        for setting in settings:
            key = setting.setting_key.replace("knowledge_graph_", "")
            value = setting.setting_value
            # Parse based on type
            if key in ["physics_enabled", "interaction_hover", "interaction_zoom", "interaction_drag", 
                      "interaction_select", "interaction_navigation_buttons", "show_legend", "show_isolated_nodes"]:
                kg_settings[key] = value.lower() == "true"
            elif key in ["spring_length", "spring_strength", "damping", "central_gravity", "node_repulsion",
                        "node_size", "node_border_width", "node_font_size", "edge_width", "edge_arrow_size",
                        "max_nodes", "max_edges", "min_edge_weight", "height"]:
                kg_settings[key] = float(value) if "." in value else int(value) if value else 0
            else:
                kg_settings[key] = value
        
        # Set defaults if not in database
        physics_enabled = kg_settings.get("physics_enabled", True)
        layout_algorithm = kg_settings.get("layout_algorithm", "force")
        spring_length = kg_settings.get("spring_length", 100)
        spring_strength = kg_settings.get("spring_strength", 0.05)
        damping = kg_settings.get("damping", 0.09)
        central_gravity = kg_settings.get("central_gravity", 0.1)
        node_repulsion = kg_settings.get("node_repulsion", 4500)
        node_shape = kg_settings.get("node_shape", "dot")
        node_size = kg_settings.get("node_size", 25)
        node_border_width = kg_settings.get("node_border_width", 2)
        node_border_color = kg_settings.get("node_border_color", "#333333")
        node_font_size = kg_settings.get("node_font_size", 14)
        node_font_color = kg_settings.get("node_font_color", "#000000")
        node_size_by = kg_settings.get("node_size_by", "degree")
        edge_color = kg_settings.get("edge_color", "#848484")
        edge_width = kg_settings.get("edge_width", 2)
        edge_arrow_type = kg_settings.get("edge_arrow_type", "arrow")
        edge_arrow_size = kg_settings.get("edge_arrow_size", 10)
        edge_smooth = kg_settings.get("edge_smooth", "dynamic")
        edge_width_by = kg_settings.get("edge_width_by", "weight")
        max_nodes = int(kg_settings.get("max_nodes", 200))
        max_edges = int(kg_settings.get("max_edges", 500))
        min_edge_weight = int(kg_settings.get("min_edge_weight", 1))
        show_isolated_nodes = kg_settings.get("show_isolated_nodes", False)
        interaction_hover = kg_settings.get("interaction_hover", True)
        interaction_zoom = kg_settings.get("interaction_zoom", True)
        interaction_drag = kg_settings.get("interaction_drag", True)
        interaction_select = kg_settings.get("interaction_select", True)
        interaction_navigation_buttons = kg_settings.get("interaction_navigation_buttons", True)
        background_color = kg_settings.get("background_color", "#ffffff")
        height = int(kg_settings.get("height", 600))
        width = kg_settings.get("width", "100%")
        show_legend = kg_settings.get("show_legend", True)
        legend_position = kg_settings.get("legend_position", "bottom")
        
        # Node type colors
        color_entity_person = kg_settings.get("color_entity_person", "#FF5733")
        color_entity_organization = kg_settings.get("color_entity_organization", "#33C1FF")
        color_entity_location = kg_settings.get("color_entity_location", "#33FF57")
        color_entity_date = kg_settings.get("color_entity_date", "#FF33A8")
        color_entity_money = kg_settings.get("color_entity_money", "#8D33FF")
        color_entity_percent = kg_settings.get("color_entity_percent", "#FFC133")
        color_entity_time = kg_settings.get("color_entity_time", "#4BFFDB")
        color_entity_facility = kg_settings.get("color_entity_facility", "#FFD733")
        color_topic = kg_settings.get("color_topic", "#FF6B6B")
        color_word = kg_settings.get("color_word", "#4ECDC4")
        
        # Build NetworkX graph
        G = nx.Graph()
        
        # Add entity nodes
        entity_count = 0
        for entity_type, entity_list in entities.items():
            if entity_list and isinstance(entity_list, list):
                for entity in entity_list[:20]:  # Limit per type
                    if entity and str(entity).strip():
                        G.add_node(str(entity), node_type="entity", entity_type=entity_type)
                        entity_count += 1
                        if entity_count >= max_nodes:
                            break
                if entity_count >= max_nodes:
                    break
        
        # Add topic nodes
        topic_count = 0
        if topics and isinstance(topics, list):
            for topic in topics[:20]:  # Limit topics
                if isinstance(topic, dict):
                    topic_label = topic.get('label', '')
                else:
                    topic_label = str(topic)
                if topic_label and topic_label.strip():
                    G.add_node(topic_label, node_type="topic")
                    topic_count += 1
                    if entity_count + topic_count >= max_nodes:
                        break
        
        # Add word cloud nodes
        word_count = 0
        if word_cloud and isinstance(word_cloud, list):
            for word_item in word_cloud[:20]:  # Limit word cloud terms
                if isinstance(word_item, dict):
                    word_term = word_item.get('term', '')
                else:
                    word_term = str(word_item)
                if word_term and word_term.strip():
                    G.add_node(word_term, node_type="word")
                    word_count += 1
                    if entity_count + topic_count + word_count >= max_nodes:
                        break
        
        # Build relationships using co-occurrence in raw text
        edge_count = 0
        for text in texts[:100]:  # Limit texts for performance
            if not text or len(text.strip()) < 10:
                continue
            
            # Find entities/topics/words that appear in this text
            nodes_in_text = []
            text_lower = text.lower()
            
            for node in G.nodes():
                node_str = str(node).lower()
                if node_str in text_lower:
                    nodes_in_text.append(node)
            
            # Connect nodes that co-occur in same text
            for i, node1 in enumerate(nodes_in_text):
                for node2 in nodes_in_text[i+1:]:
                    if G.has_edge(node1, node2):
                        # Increment weight
                        G[node1][node2]['weight'] = G[node1][node2].get('weight', 1) + 1
                    else:
                        # Add new edge
                        if edge_count < max_edges:
                            G.add_edge(node1, node2, weight=1, relationship="co_occurs_with")
                            edge_count += 1
        
        # Filter edges by minimum weight
        if min_edge_weight > 1:
            edges_to_remove = [(u, v) for u, v, d in G.edges(data=True) if d.get('weight', 1) < min_edge_weight]
            G.remove_edges_from(edges_to_remove)
        
        # Remove isolated nodes if not wanted
        if not show_isolated_nodes:
            isolated = list(nx.isolates(G))
            G.remove_nodes_from(isolated)
        
        # Create pyvis network
        net = Network(
            height=f"{height}px",
            width=width,
            bgcolor=background_color,
            font_color=node_font_color,
            directed=False
        )
        
        # Configure physics
        if physics_enabled:
            net.set_options(f"""
            {{
              "physics": {{
                "enabled": true,
                "barnesHut": {{
                  "gravitationalConstant": -{node_repulsion},
                  "centralGravity": {central_gravity},
                  "springLength": {spring_length},
                  "springConstant": {spring_strength},
                  "damping": {damping}
                }}
              }},
              "interaction": {{
                "hover": {str(interaction_hover).lower()},
                "zoomView": {str(interaction_zoom).lower()},
                "dragView": {str(interaction_drag).lower()},
                "selectConnectedEdges": {str(interaction_select).lower()},
                "navigationButtons": {str(interaction_navigation_buttons).lower()}
              }}
            }}
            """)
        else:
            net.set_options(f"""
            {{
              "physics": {{
                "enabled": false
              }},
              "interaction": {{
                "hover": {str(interaction_hover).lower()},
                "zoomView": {str(interaction_zoom).lower()},
                "dragView": {str(interaction_drag).lower()},
                "selectConnectedEdges": {str(interaction_select).lower()},
                "navigationButtons": {str(interaction_navigation_buttons).lower()}
              }}
            }}
            """)
        
        # Add nodes with colors by type
        node_colors = {
            "person": color_entity_person,
            "organization": color_entity_organization,
            "location": color_entity_location,
            "date": color_entity_date,
            "money": color_entity_money,
            "percent": color_entity_percent,
            "time": color_entity_time,
            "facility": color_entity_facility,
            "topic": color_topic,
            "word": color_word,
        }
        
        for node, data in G.nodes(data=True):
            node_type = data.get('node_type', 'unknown')
            entity_type = data.get('entity_type', '')
            
            # Determine color
            if node_type == "entity" and entity_type:
                color = node_colors.get(entity_type, "#CCCCCC")
            elif node_type == "topic":
                color = color_topic
            elif node_type == "word":
                color = color_word
            else:
                color = "#CCCCCC"
            
            # Calculate size based on degree if enabled
            if node_size_by == "degree":
                degree = G.degree(node)
                size = max(node_size * 0.5, min(node_size * 2, node_size + degree * 2))
            elif node_size_by == "weight":
                # Use average edge weight
                edges = G.edges(node, data=True)
                if edges:
                    avg_weight = sum(d.get('weight', 1) for _, _, d in edges) / len(edges)
                    size = max(node_size * 0.5, min(node_size * 2, node_size + avg_weight * 2))
                else:
                    size = node_size
            else:
                size = node_size
            
            net.add_node(
                str(node),
                label=str(node),
                color=color,
                size=size,
                shape=node_shape,
                borderWidth=node_border_width,
                borderColor=node_border_color,
                font={"size": node_font_size, "color": node_font_color},
                title=f"{node_type}: {node}"
            )
        
        # Add edges with weights
        for edge in G.edges(data=True):
            source, target, data = edge
            weight = data.get('weight', 1)
            relationship = data.get('relationship', 'related')
            
            # Calculate edge width
            if edge_width_by == "weight":
                width_val = max(1, min(10, edge_width + weight))
            else:
                width_val = edge_width
            
            net.add_edge(
                str(source),
                str(target),
                value=weight,
                width=width_val,
                color=edge_color,
                arrows=edge_arrow_type if edge_arrow_type != "none" else False,
                arrowStrikethrough=False,
                smooth={"type": edge_smooth, "roundness": 0.5},
                title=f"{relationship} (weight: {weight})"
            )
        
        # Generate HTML
        html = net.generate_html()
        
        # Add legend if enabled
        if show_legend:
            legend_html = f"""
            <div style="position: absolute; {legend_position}: 10px; left: 10px; background: white; padding: 10px; border: 1px solid #ccc; border-radius: 5px; font-size: 12px; z-index: 1000;">
                <strong>Legend:</strong><br/>
                <span style="color: {color_entity_person};">●</span> Person<br/>
                <span style="color: {color_entity_organization};">●</span> Organization<br/>
                <span style="color: {color_entity_location};">●</span> Location<br/>
                <span style="color: {color_entity_date};">●</span> Date<br/>
                <span style="color: {color_topic};">●</span> Topic<br/>
                <span style="color: {color_word};">●</span> Word<br/>
            </div>
            """
            # Insert legend before closing body tag
            html = html.replace("</body>", legend_html + "</body>")
        
        response = HTMLResponse(content=html)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
        
    except ImportError as e:
        logger.error(f"Required packages not available: {e}")
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>Required packages not available: {str(e)}</p><p>Please install: pip install networkx pyvis</p></body></html>",
            status_code=503
        )
    except Exception as e:
        logger.error(f"Error generating knowledge graph visualization: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>{str(e)}</p><p>Check backend logs for details.</p></body></html>",
            status_code=500
        )

# Research Agent Recommendations endpoint
