"""
Keyword and abbreviation expansions for search queries

This module provides expansions for common abbreviations and acronyms
to improve search query relevance. These expansions are used BEFORE
searching (to improve DuckDuckGo results), not for entity extraction.

Entity extraction (NLTK) should handle common terms naturally, but
search engines often work better with expanded terms.

Add new abbreviations here as needed.
"""

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

def expand_keyword(keyword: str) -> str:
    """
    Expand a single keyword if it's a known abbreviation
    
    Args:
        keyword: The keyword to expand
        
    Returns:
        Expanded keyword if found, otherwise original keyword
    """
    # Check exact match (case-insensitive)
    expanded = ALL_EXPANSIONS.get(keyword.upper())
    if expanded:
        return expanded
    
    # Check if keyword contains abbreviation (for queries like "WW2 history")
    keyword_upper = keyword.upper()
    for abbrev, expansion in ALL_EXPANSIONS.items():
        if abbrev in keyword_upper:
            # Replace abbreviation in keyword
            return keyword.replace(abbrev, expansion).replace(abbrev.lower(), expansion)
    
    return keyword

def expand_query(query: str) -> str:
    """
    Expand abbreviations in a search query string
    
    Args:
        query: The search query string
        
    Returns:
        Query with abbreviations expanded
    """
    if not query:
        return query
    
    expanded_query = query
    query_upper = query.upper()
    
    # Check for abbreviations in query
    for abbrev, expansion in ALL_EXPANSIONS.items():
        if abbrev in query_upper:
            # Replace abbreviation (case-insensitive)
            expanded_query = expanded_query.replace(abbrev, expansion)
            expanded_query = expanded_query.replace(abbrev.lower(), expansion)
            expanded_query = expanded_query.replace(abbrev.capitalize(), expansion)
    
    return expanded_query

