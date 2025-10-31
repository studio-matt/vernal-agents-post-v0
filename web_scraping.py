"""
Web Scraping Module for Campaign Analysis
Implements DuckDuckGo search and Playwright-based web scraping
"""

import logging
import re
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse
from datetime import datetime

logger = logging.getLogger(__name__)

# Use new ddgs package (duckduckgo_search is deprecated and causes warnings)
DDGS = None
try:
    from ddgs import DDGS  # New package name
    logger.info("✅ Using ddgs package for DuckDuckGo search")
except ImportError:
    logger.error("ddgs package not available. Install with: pip install ddgs")
    DDGS = None

try:
    from playwright.sync_api import sync_playwright, Browser, Page
except ImportError:
    logging.warning("playwright not available - scraping will be disabled")
    sync_playwright = None

logger = logging.getLogger(__name__)

def search_duckduckgo(keywords: List[str], query: str = "", max_results: int = 10) -> List[str]:
    """
    Search DuckDuckGo for URLs based on keywords and query
    
    Args:
        keywords: List of keywords to search for
        query: Additional context query string
        max_results: Maximum number of URLs to return
        
    Returns:
        List of URLs from search results
    """
    if DDGS is None:
        logger.error("duckduckgo_search library not available")
        return []
    
    try:
        # Combine keywords and query into search string
        search_terms = []
        if query:
            search_terms.append(query)
        if keywords:
            search_terms.extend(keywords[:5])  # Limit to 5 keywords to avoid overly long queries
        
        search_query = " ".join(search_terms[:10])  # Limit total terms
        
        if not search_query.strip():
            logger.warning("Empty search query, returning empty results")
            return []
        
        logger.info(f"🔍 Searching DuckDuckGo for: '{search_query}' (max_results={max_results})")
        
        results = []
        try:
            with DDGS() as ddgs:
                # Use text() method - returns list of result dictionaries (not generator in newer versions)
                search_results = ddgs.text(search_query, max_results=max_results)
                
                # Handle both list and generator returns
                if not isinstance(search_results, (list, tuple)):
                    search_results = list(search_results)
                
                count = 0
                for result in search_results:
                    # ddgs.text() returns dictionaries with different key formats
                    url = None
                    if isinstance(result, dict):
                        # Try multiple possible keys
                        url = result.get('href') or result.get('url') or result.get('link') or result.get('url')
                        
                        # Some versions return nested structures
                        if not url and isinstance(result.get('body'), dict):
                            url = result['body'].get('href') or result['body'].get('url')
                    
                    if url and isinstance(url, str) and url.startswith(('http://', 'https://')):
                        # Avoid duplicates
                        if url not in results:
                            results.append(url)
                            count += 1
                            logger.debug(f"Found URL: {url}")
                            if count >= max_results:
                                break
                    
                    # Safety check to avoid infinite loops
                    if count > max_results * 2:
                        logger.warning(f"Search returning too many results, limiting to {max_results}")
                        break
                
                if count == 0:
                    logger.warning(f"No URLs found in search results. Search query: '{search_query}'")
                    logger.debug(f"Sample result structure: {list(search_results)[:1] if hasattr(search_results, '__iter__') else 'N/A'}")
                        
        except Exception as search_err:
            logger.error(f"Error in DuckDuckGo search execution: {search_err}")
            import traceback
            logger.error(traceback.format_exc())
        
        logger.info(f"✅ DuckDuckGo search returned {len(results)} URLs")
        return results[:max_results]
    
    except Exception as e:
        logger.error(f"❌ Error searching DuckDuckGo: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def extract_links_from_html(html: str, base_url: str, max_links: int = 10) -> List[str]:
    """
    Extract links from HTML content
    
    Args:
        html: HTML content
        base_url: Base URL for resolving relative links
        max_links: Maximum number of links to return
        
    Returns:
        List of absolute URLs
    """
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)
            # Only include http/https URLs
            parsed = urlparse(absolute_url)
            if parsed.scheme in ('http', 'https') and parsed.netloc:
                # Same domain only (for depth control)
                if parsed.netloc == urlparse(base_url).netloc:
                    links.append(absolute_url)
        
        # Deduplicate and limit
        unique_links = list(dict.fromkeys(links))[:max_links]
        logger.debug(f"Extracted {len(unique_links)} links from {base_url}")
        return unique_links
    
    except Exception as e:
        logger.warning(f"Error extracting links from {base_url}: {e}")
        return []

def scrape_with_playwright(
    url: str,
    include_images: bool = False,
    include_links: bool = False,
    timeout: int = 30000
) -> Dict[str, any]:
    """
    Scrape a single URL using Playwright
    
    Args:
        url: URL to scrape
        include_images: Whether to extract image URLs
        include_links: Whether to extract links
        timeout: Page load timeout in milliseconds
        
    Returns:
        Dictionary with:
        - text: Extracted text content
        - html: Raw HTML (optional)
        - images: List of image URLs (if include_images=True)
        - links: List of extracted links (if include_links=True)
        - error: Error message if scraping failed
    """
    if sync_playwright is None:
        return {
            "text": "",
            "html": None,
            "images": [],
            "links": [],
            "error": "Playwright not available"
        }
    
    result = {
        "text": "",
        "html": None,
        "images": [],
        "links": [],
        "error": None
    }
    
    try:
        with sync_playwright() as p:
            # Launch browser in headless mode
            # Note: Playwright browsers must be installed via: playwright install chromium
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as launch_err:
                logger.error(f"Failed to launch Playwright browser: {launch_err}")
                logger.error("Run 'playwright install chromium' to install browsers")
                return {
                    "text": "",
                    "html": None,
                    "images": [],
                    "links": [],
                    "error": f"Playwright browser not installed: {str(launch_err)}"
                }
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            
            # Navigate to URL
            logger.debug(f"🌐 Navigating to: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            
            # Wait a bit for JavaScript to load content
            page.wait_for_timeout(2000)
            
            # Extract text content
            try:
                # Try to get main content area (common selectors)
                content_selectors = [
                    'article', 'main', '[role="main"]', 
                    '.content', '#content', '.post-content',
                    '.article-content', '.entry-content'
                ]
                
                text_content = ""
                for selector in content_selectors:
                    elements = page.query_selector_all(selector)
                    if elements:
                        for element in elements:
                            text = element.inner_text()
                            if len(text) > len(text_content):
                                text_content = text
                        break
                
                # Fallback to body if no content found
                if not text_content:
                    body = page.query_selector('body')
                    if body:
                        text_content = body.inner_text()
                
                # Clean up text
                text_content = re.sub(r'\s+', ' ', text_content).strip()
                result["text"] = text_content
                
            except Exception as e:
                logger.warning(f"Error extracting text from {url}: {e}")
                result["error"] = f"Text extraction error: {str(e)}"
            
            # Extract images if requested
            if include_images:
                try:
                    images = page.query_selector_all('img[src]')
                    image_urls = []
                    for img in images:
                        src = img.get_attribute('src')
                        if src:
                            absolute_url = urljoin(url, src)
                            if absolute_url.startswith(('http://', 'https://')):
                                image_urls.append(absolute_url)
                    result["images"] = list(dict.fromkeys(image_urls))[:50]  # Limit to 50 images
                    logger.debug(f"Extracted {len(result['images'])} images from {url}")
                except Exception as e:
                    logger.warning(f"Error extracting images from {url}: {e}")
            
            # Extract links if requested
            if include_links:
                try:
                    html_content = page.content()
                    result["html"] = html_content
                    links = extract_links_from_html(html_content, url, max_links=20)
                    result["links"] = links
                except Exception as e:
                    logger.warning(f"Error extracting links from {url}: {e}")
            
            browser.close()
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error scraping {url}: {error_msg}")
        result["error"] = error_msg
        result["text"] = f"Error scraping URL: {error_msg}"
    
    return result

def scrape_urls_recursive(
    urls: List[str],
    depth: int = 1,
    max_pages: int = 10,
    include_images: bool = False,
    include_links: bool = False,
    visited: Optional[Set[str]] = None,
    current_depth: int = 0
) -> List[Dict[str, any]]:
    """
    Recursively scrape URLs with depth control
    
    Args:
        urls: List of URLs to scrape
        depth: Maximum depth to follow links (1 = only initial URLs)
        max_pages: Maximum total pages to scrape
        include_images: Whether to extract images
        include_links: Whether to extract links (required for depth > 1)
        visited: Set of already visited URLs (for deduplication)
        current_depth: Current depth level (internal use)
        
    Returns:
        List of scraped data dictionaries
    """
    if visited is None:
        visited = set()
    
    if current_depth >= depth or len(visited) >= max_pages:
        return []
    
    results = []
    
    for url in urls:
        # Check limits
        if len(visited) >= max_pages:
            logger.info(f"Reached max_pages limit ({max_pages}), stopping")
            break
        
        # Skip if already visited
        if url in visited:
            continue
        
        # Mark as visited
        visited.add(url)
        
        logger.info(f"📄 Scraping [{current_depth}/{depth}]: {url}")
        
        # Scrape the URL
        scraped_data = scrape_with_playwright(
            url,
            include_images=include_images,
            include_links=include_links
        )
        
        # Add URL and metadata to result
        scraped_data["url"] = url
        scraped_data["depth"] = current_depth
        scraped_data["scraped_at"] = datetime.utcnow().isoformat()
        
        results.append(scraped_data)
        
        # If depth > 1 and include_links=True, recursively scrape links
        if depth > 1 and include_links and current_depth < (depth - 1):
            links = scraped_data.get("links", [])
            if links:
                # Limit links to follow
                links_to_follow = links[:5]  # Limit to 5 links per page
                logger.debug(f"Following {len(links_to_follow)} links from {url}")
                recursive_results = scrape_urls_recursive(
                    links_to_follow,
                    depth=depth,
                    max_pages=max_pages,
                    include_images=include_images,
                    include_links=include_links,
                    visited=visited,
                    current_depth=current_depth + 1
                )
                results.extend(recursive_results)
    
    return results

def scrape_campaign_data(
    keywords: List[str] = None,
    urls: List[str] = None,
    query: str = "",
    depth: int = 1,
    max_pages: int = 10,
    include_images: bool = False,
    include_links: bool = False
) -> List[Dict[str, any]]:
    """
    Main function to scrape campaign data
    
    Combines DuckDuckGo search (for keywords) and Playwright scraping
    
    Args:
        keywords: List of keywords to search for
        urls: Direct URLs to scrape (optional)
        query: Additional context query string
        depth: Web scraping depth (1 = only initial URLs)
        max_pages: Maximum pages to scrape
        include_images: Whether to extract images
        include_links: Whether to extract links
        
    Returns:
        List of scraped data dictionaries
    """
    all_urls = []
    
    # Add direct URLs if provided
    if urls:
        all_urls.extend(urls)
    
    # Search for keywords if provided
    if keywords:
        search_urls = search_duckduckgo(keywords, query=query, max_results=max_pages)
        all_urls.extend(search_urls)
    
    # Deduplicate URLs
    unique_urls = list(dict.fromkeys(all_urls))[:max_pages]
    
    if not unique_urls:
        logger.warning("No URLs to scrape")
        return []
    
    logger.info(f"🚀 Starting scraping for {len(unique_urls)} URLs (depth={depth}, max_pages={max_pages})")
    
    # Scrape URLs recursively
    results = scrape_urls_recursive(
        unique_urls,
        depth=depth,
        max_pages=max_pages,
        include_images=include_images,
        include_links=include_links
    )
    
    logger.info(f"✅ Scraping complete: {len(results)} pages scraped")
    
    return results

