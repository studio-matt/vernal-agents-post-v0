"""
Keyword and abbreviation expansions for search queries

This module provides expansions for common abbreviations and acronyms
to improve search query relevance. These expansions are used BEFORE
searching (to improve DuckDuckGo results), not for entity extraction.

Entity extraction (NLTK) should handle common terms naturally, but
search engines often work better with expanded terms.

Features:
- Manual dictionary (fast, free, reliable)
- LLM-based expansion for unknown abbreviations (if API key available)
- Result caching to avoid repeated API calls
- Graceful fallback if LLM unavailable

Add new abbreviations to the dictionaries below as needed.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def _get_keyword_expansion_prompt() -> str:
    """
    Get the keyword expansion prompt from database, with fallback to default.
    """
    # Default prompt (fallback)
    default_prompt = """Expand this abbreviation to its full form. Return ONLY the expansion, nothing else. If it's not an abbreviation, return the original word.

Examples:
- WW2 → World War 2
- AI → artificial intelligence
- CEO → Chief Executive Officer
- NASA → National Aeronautics and Space Administration

Abbreviation: {keyword}

Expansion:"""
    
    # Try to load from database
    try:
        from database import SessionLocal
        db = SessionLocal()
        try:
            from models import SystemSettings
            setting = db.query(SystemSettings).filter(
                SystemSettings.setting_key == "keyword_expansion_prompt"
            ).first()
            
            if setting and setting.setting_value:
                logger.debug("✅ Loaded keyword expansion prompt from database")
                return setting.setting_value
            else:
                logger.debug("⚠️ Keyword expansion prompt not found in database, using default")
        except Exception as db_err:
            logger.warning(f"⚠️ Failed to load prompt from database: {db_err}, using default")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"⚠️ Database not available for prompt loading: {e}, using default")
    
    return default_prompt

# In-memory cache for LLM expansions (avoid repeated API calls)
_llm_cache: dict[str, str] = {}

# Historical/Military abbreviations
HISTORICAL = {
    "WW2": "World War 2",
    "WWII": "World War 2",
    "WW1": "World War 1",
    "WWI": "World War 1",
    "WW3": "World War 3",
    "WWIII": "World War 3",
}

# Technology abbreviations
TECHNOLOGY = {
    "AI": "artificial intelligence",
    "ML": "machine learning",
    "API": "application programming interface",
    "REST": "representational state transfer",
    "JSON": "JavaScript Object Notation",
    "XML": "eXtensible Markup Language",
    "HTML": "HyperText Markup Language",
    "CSS": "Cascading Style Sheets",
    "JS": "JavaScript",
    "TS": "TypeScript",
    "SQL": "Structured Query Language",
    "NoSQL": "Not Only SQL",
    "HTTP": "HyperText Transfer Protocol",
    "HTTPS": "HyperText Transfer Protocol Secure",
    "URL": "Uniform Resource Locator",
    "URI": "Uniform Resource Identifier",
    "DNS": "Domain Name System",
    "CDN": "Content Delivery Network",
    "SaaS": "Software as a Service",
    "PaaS": "Platform as a Service",
    "IaaS": "Infrastructure as a Service",
}

# Business/Finance abbreviations
BUSINESS = {
    "CEO": "Chief Executive Officer",
    "CFO": "Chief Financial Officer",
    "CTO": "Chief Technology Officer",
    "IPO": "Initial Public Offering",
    "ROI": "Return on Investment",
    "KPI": "Key Performance Indicator",
    "B2B": "Business to Business",
    "B2C": "Business to Consumer",
    "GDP": "Gross Domestic Product",
}

# Science/Medical abbreviations
SCIENCE = {
    "DNA": "deoxyribonucleic acid",
    "RNA": "ribonucleic acid",
    "COVID": "coronavirus disease",
    "HIV": "human immunodeficiency virus",
    "AIDS": "acquired immunodeficiency syndrome",
    "NASA": "National Aeronautics and Space Administration",
    "STEM": "Science Technology Engineering Mathematics",
}

# Geographic abbreviations
GEOGRAPHIC = {
    "USA": "United States",
    "US": "United States",
    "UK": "United Kingdom",
    "EU": "European Union",
    "UN": "United Nations",
    "NATO": "North Atlantic Treaty Organization",
}

# Combine all expansions into a single dictionary
ALL_EXPANSIONS = {
    **HISTORICAL,
    **TECHNOLOGY,
    **BUSINESS,
    **SCIENCE,
    **GEOGRAPHIC,
}

def _expand_with_llm(keyword: str) -> Optional[str]:
    """
    Use LLM to expand an unknown abbreviation
    
    Args:
        keyword: The abbreviation to expand
        
    Returns:
        Expansion if LLM succeeds, None otherwise
    """
    # Check cache first
    cache_key = keyword.upper()
    if cache_key in _llm_cache:
        logger.debug(f"Using cached LLM expansion: {keyword} -> {_llm_cache[cache_key]}")
        return _llm_cache[cache_key]
    
    # Check if API key is available
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.debug(f"No OPENAI_API_KEY available, skipping LLM expansion for '{keyword}'")
        return None
    
    try:
        from langchain_openai import ChatOpenAI
        
        # Get prompt from database, with fallback to default
        prompt_template = _get_keyword_expansion_prompt()
        
        # Format prompt with keyword
        prompt = prompt_template.format(keyword=keyword)
        
        # Use cheap, fast model for simple abbreviation expansion
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=api_key,
            temperature=0.1,  # Low temperature for factual expansion
            max_tokens=20     # Very short response needed
        )
        
        response = llm.invoke(prompt)
        expansion = response.content.strip()
        
        # Validate: expansion should be longer than original and not identical
        if expansion and len(expansion) > len(keyword) and expansion.lower() != keyword.lower():
            # Cache the result
            _llm_cache[cache_key] = expansion
            logger.info(f"✅ LLM expanded '{keyword}' → '{expansion}'")
            return expansion
        else:
            logger.debug(f"LLM returned invalid expansion for '{keyword}': '{expansion}'")
            # Cache None to avoid repeated failed attempts
            _llm_cache[cache_key] = keyword
            return None
            
    except Exception as e:
        logger.warning(f"LLM expansion failed for '{keyword}': {e}")
        # Cache None to avoid repeated failed attempts
        _llm_cache[cache_key] = keyword
        return None

def expand_keyword(keyword: str, use_llm: bool = True) -> str:
    """
    Expand a single keyword if it's a known abbreviation
    
    Args:
        keyword: The keyword to expand
        use_llm: Whether to use LLM for unknown abbreviations (default: True)
        
    Returns:
        Expanded keyword if found, otherwise original keyword (or LLM expansion if available)
    """
    # Step 1: Check manual dictionary (fast, free)
    expanded = ALL_EXPANSIONS.get(keyword.upper())
    if expanded:
        return expanded
    
    # Step 2: Check if keyword contains abbreviation (for queries like "WW2 history")
    # CRITICAL: Use word boundaries to avoid partial matches
    import re
    keyword_upper = keyword.upper()
    for abbrev, expansion in ALL_EXPANSIONS.items():
        # Only replace if abbreviation is a complete word (not part of another word)
        pattern = r'\b' + re.escape(abbrev) + r'\b'
        if re.search(pattern, keyword_upper):
            # Replace whole word only (case-insensitive)
            return re.sub(pattern, expansion, keyword, flags=re.IGNORECASE)
    
    # Step 3: Try LLM expansion if enabled and keyword looks like an abbreviation
    # (all caps, short, no spaces = likely abbreviation)
    if use_llm and keyword.isupper() and len(keyword) <= 10 and ' ' not in keyword:
        llm_expansion = _expand_with_llm(keyword)
        if llm_expansion:
            return llm_expansion
    
    # Step 4: Return original if no expansion found
    return keyword

def expand_query(query: str, use_llm: bool = True) -> str:
    """
    Expand abbreviations in a search query string
    
    Args:
        query: The search query string
        use_llm: Whether to use LLM for unknown abbreviations (default: True)
        
    Returns:
        Query with abbreviations expanded
    """
    if not query:
        return query
    
    expanded_query = query
    query_upper = query.upper()
    
    # Step 1: Check manual dictionary (fast, free)
    # CRITICAL: Use word boundaries to avoid partial matches (e.g., "CTO" in "collectors")
    import re
    for abbrev, expansion in ALL_EXPANSIONS.items():
        # Only replace if abbreviation is a complete word (not part of another word)
        # Use word boundaries (\b) to match whole words only
        pattern = r'\b' + re.escape(abbrev) + r'\b'
        if re.search(pattern, query_upper):
            # Replace whole word only (case-insensitive)
            expanded_query = re.sub(pattern, expansion, query_upper, flags=re.IGNORECASE)
    
    # Step 2: Try LLM for unknown abbreviations (if enabled)
    # Extract potential abbreviations (all caps, 2-10 chars, no spaces)
    if use_llm:
        import re
        # Find potential abbreviations in query
        abbrev_pattern = r'\b[A-Z]{2,10}\b'
        potential_abbrevs = re.findall(abbrev_pattern, expanded_query)
        
        for abbrev in potential_abbrevs:
            # Skip if already in manual dictionary
            if abbrev.upper() in ALL_EXPANSIONS:
                continue
            
            # Try LLM expansion
            llm_expansion = _expand_with_llm(abbrev)
            if llm_expansion and llm_expansion != abbrev:
                # Replace in query
                expanded_query = expanded_query.replace(abbrev, llm_expansion)
    
    return expanded_query

