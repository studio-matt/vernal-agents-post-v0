"""
Gap Analysis for Site Builder Campaign Type
Identifies content gaps by comparing existing site content to ideal knowledge graph coverage
"""

import logging
from typing import List, Dict, Set, Optional
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


def build_ideal_knowledge_graph(target_keywords: List[str], existing_topics: List[str] = None) -> Dict:
    """
    Build an ideal knowledge graph structure from target keywords
    
    Args:
        target_keywords: List of target keywords/phrases for content planning
        existing_topics: Optional list of existing topics to consider connections
    
    Returns:
        Dictionary representing ideal knowledge graph structure
    """
    ideal_kg = {
        "nodes": [],
        "edges": [],
        "keyword_coverage": {}
    }
    
    # Create nodes for each target keyword
    for keyword in target_keywords:
        keyword_lower = keyword.lower().strip()
        ideal_kg["nodes"].append({
            "id": keyword_lower,
            "label": keyword,
            "type": "target_keyword",
            "priority": "high"
        })
        ideal_kg["keyword_coverage"][keyword_lower] = {
            "covered": False,
            "related_topics": []
        }
    
    # If we have existing topics, create connections
    if existing_topics:
        for topic in existing_topics:
            topic_lower = topic.lower().strip()
            # Check if topic relates to any target keyword
            for keyword in target_keywords:
                keyword_lower = keyword.lower().strip()
                # Simple keyword matching (can be enhanced with semantic similarity)
                if keyword_lower in topic_lower or topic_lower in keyword_lower:
                    ideal_kg["edges"].append({
                        "source": keyword_lower,
                        "target": topic_lower,
                        "type": "related",
                        "strength": 0.5
                    })
                    ideal_kg["keyword_coverage"][keyword_lower]["related_topics"].append(topic)
    
    return ideal_kg


def analyze_knowledge_graph_coverage(
    existing_kg: Dict,
    ideal_kg: Dict,
    target_keywords: List[str]
) -> Dict[str, any]:
    """
    Analyze how well existing knowledge graph covers ideal structure
    
    Args:
        existing_kg: Existing knowledge graph from site content
        ideal_kg: Ideal knowledge graph built from target keywords
        target_keywords: List of target keywords
    
    Returns:
        Dictionary with coverage analysis
    """
    coverage_analysis = {
        "covered_keywords": [],
        "missing_keywords": [],
        "weak_connections": [],
        "coverage_score": 0.0
    }
    
    existing_nodes = {node.get("id", "").lower(): node for node in existing_kg.get("nodes", [])}
    existing_edges = existing_kg.get("edges", [])
    
    # Check keyword coverage
    for keyword in target_keywords:
        keyword_lower = keyword.lower().strip()
        if keyword_lower in existing_nodes:
            coverage_analysis["covered_keywords"].append(keyword)
        else:
            coverage_analysis["missing_keywords"].append(keyword)
    
    # Check for weak connections (keywords with few related topics)
    for keyword in target_keywords:
        keyword_lower = keyword.lower().strip()
        related_count = sum(1 for edge in existing_edges 
                          if edge.get("source", "").lower() == keyword_lower 
                          or edge.get("target", "").lower() == keyword_lower)
        if related_count < 2:  # Threshold for "weak"
            coverage_analysis["weak_connections"].append({
                "keyword": keyword,
                "connection_count": related_count
            })
    
    # Calculate coverage score
    total_keywords = len(target_keywords)
    if total_keywords > 0:
        coverage_analysis["coverage_score"] = len(coverage_analysis["covered_keywords"]) / total_keywords
    
    return coverage_analysis


def identify_content_gaps(
    existing_topics: List[str],
    knowledge_graph: Dict,
    target_keywords: List[str] = None,
    existing_urls: List[str] = None
) -> List[Dict]:
    """
    Identify gaps in content coverage
    
    Args:
        existing_topics: List of topics currently covered on the site
        knowledge_graph: Existing knowledge graph structure
        target_keywords: Optional list of target keywords for gap analysis
        existing_urls: Optional list of existing URLs (for context)
    
    Returns:
        List of gap objects with priority and reasoning
    """
    gaps = []
    
    if not target_keywords:
        logger.warning("No target keywords provided for gap analysis")
        return gaps
    
    # Build ideal knowledge graph
    ideal_kg = build_ideal_knowledge_graph(target_keywords, existing_topics)
    
    # Analyze coverage
    coverage = analyze_knowledge_graph_coverage(knowledge_graph, ideal_kg, target_keywords)
    
    # Create gap entries for missing keywords
    for keyword in coverage["missing_keywords"]:
        gaps.append({
            "gap_topic": keyword,
            "reason": f"Missing content for target keyword: {keyword}",
            "priority": "high",
            "related_existing": [],
            "keyword": keyword,
            "type": "missing_keyword"
        })
    
    # Create gap entries for weak connections
    for weak_conn in coverage["weak_connections"]:
        keyword = weak_conn["keyword"]
        # Find related existing topics
        related = [t for t in existing_topics if keyword.lower() in t.lower() or t.lower() in keyword.lower()]
        gaps.append({
            "gap_topic": f"Expand {keyword} coverage",
            "reason": f"Keyword '{keyword}' has only {weak_conn['connection_count']} connections in knowledge graph",
            "priority": "medium",
            "related_existing": related[:3],  # Top 3 related
            "keyword": keyword,
            "type": "weak_connection"
        })
    
    # Identify semantic gaps (topics that should connect but don't)
    existing_topic_set = {t.lower() for t in existing_topics}
    for i, keyword1 in enumerate(target_keywords):
        for keyword2 in target_keywords[i+1:]:
            # Check if these keywords should be connected but aren't
            keyword1_lower = keyword1.lower()
            keyword2_lower = keyword2.lower()
            
            # Look for existing topics that might bridge these keywords
            bridging_topics = [t for t in existing_topics 
                             if keyword1_lower in t.lower() or keyword2_lower in t.lower()]
            
            if not bridging_topics:
                # Potential gap: keywords that should be connected
                gaps.append({
                    "gap_topic": f"Bridge {keyword1} and {keyword2}",
                    "reason": f"Missing content connecting '{keyword1}' and '{keyword2}'",
                    "priority": "medium",
                    "related_existing": [],
                    "keyword": f"{keyword1}, {keyword2}",
                    "type": "semantic_gap"
                })
    
    # Sort gaps by priority (high > medium > low)
    priority_order = {"high": 3, "medium": 2, "low": 1}
    gaps.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 0), reverse=True)
    
    logger.info(f"Identified {len(gaps)} content gaps from {len(target_keywords)} target keywords")
    return gaps


def rank_gaps_by_priority(
    gaps: List[Dict],
    top_n: Optional[int] = None
) -> List[Dict]:
    """
    Rank gaps by priority and return top N
    
    Args:
        gaps: List of gap dictionaries
        top_n: Number of top gaps to return (None = all)
    
    Returns:
        Ranked list of gaps
    """
    # Priority scoring: high=3, medium=2, low=1
    priority_scores = {"high": 3, "medium": 2, "low": 1}
    
    # Score each gap
    for gap in gaps:
        base_score = priority_scores.get(gap.get("priority", "low"), 1)
        # Boost score if it has related existing topics (easier to build on)
        if gap.get("related_existing"):
            base_score += 0.5
        gap["_priority_score"] = base_score
    
    # Sort by score
    ranked = sorted(gaps, key=lambda x: x.get("_priority_score", 0), reverse=True)
    
    # Remove internal scoring field
    for gap in ranked:
        gap.pop("_priority_score", None)
    
    if top_n:
        return ranked[:top_n]
    return ranked


if __name__ == "__main__":
    # Test gap analysis
    existing_topics = ["AI", "Machine Learning", "Healthcare", "Data Science"]
    target_keywords = ["AI Ethics", "Healthcare AI", "Machine Learning Applications"]
    
    # Mock knowledge graph
    kg = {
        "nodes": [
            {"id": "ai", "label": "AI"},
            {"id": "healthcare", "label": "Healthcare"}
        ],
        "edges": [
            {"source": "ai", "target": "healthcare", "type": "related"}
        ]
    }
    
    gaps = identify_content_gaps(existing_topics, kg, target_keywords)
    print(f"\nFound {len(gaps)} gaps:")
    for gap in gaps:
        print(f"  - {gap['gap_topic']}: {gap['reason']} (Priority: {gap['priority']})")
    
    top_gaps = rank_gaps_by_priority(gaps, top_n=5)
    print(f"\nTop 5 gaps:")
    for gap in top_gaps:
        print(f"  - {gap['gap_topic']}")

