"""
Sitemap Parser for Site Builder Campaign Type
Parses sitemap.xml files to extract all URLs from a website
"""

import logging
import xml.etree.ElementTree as ET
from typing import List, Set, Tuple, Optional
from urllib.parse import urljoin, urlparse
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Namespaces for sitemap XML
SITEMAP_NS = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def create_session_with_retry() -> requests.Session:
    """Create a requests session with retry strategy"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def find_sitemap_urls(base_url: str) -> List[str]:
    """
    Find potential sitemap URLs for a given base URL
    
    Args:
        base_url: Base URL of the website (e.g., "https://example.com")
    
    Returns:
        List of potential sitemap URLs to try
    """
    base_url = base_url.rstrip("/")
    return [
        f"{base_url}/sitemap.xml",
        f"{base_url}/sitemap_index.xml",
        f"{base_url}/sitemap-index.xml",
        f"{base_url}/sitemaps.xml",
        f"{base_url}/robots.txt",  # Will check robots.txt for sitemap location
    ]


def get_sitemap_from_robots_txt(robots_url: str) -> List[str]:
    """
    Parse robots.txt to find sitemap URLs
    
    Args:
        robots_url: URL to robots.txt file
    
    Returns:
        List of sitemap URLs found in robots.txt
    """
    sitemap_urls = []
    try:
        session = create_session_with_retry()
        response = session.get(robots_url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (compatible; SiteBuilderBot/1.0)"
        })
        response.raise_for_status()
        
        for line in response.text.split("\n"):
            line = line.strip()
            if line.lower().startswith("sitemap:"):
                sitemap_url = line.split(":", 1)[1].strip()
                sitemap_urls.append(sitemap_url)
                logger.info(f"Found sitemap in robots.txt: {sitemap_url}")
    except Exception as e:
        logger.warning(f"Could not parse robots.txt from {robots_url}: {e}")
    
    return sitemap_urls


def parse_sitemap_index(sitemap_url: str) -> List[str]:
    """
    Parse a sitemap index file and return URLs of individual sitemaps
    
    Args:
        sitemap_url: URL to sitemap index XML file
    
    Returns:
        List of sitemap URLs from the index
    """
    sitemap_urls = []
    try:
        session = create_session_with_retry()
        response = session.get(sitemap_url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (compatible; SiteBuilderBot/1.0)"
        })
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        
        # Check if it's a sitemap index
        if root.tag.endswith("sitemapindex"):
            # Try namespaced first
            sitemap_elems = root.findall(".//sitemap:sitemap", SITEMAP_NS)
            if not sitemap_elems:
                # Fallback: try without namespace
                sitemap_elems = root.findall(".//sitemap")
            
            for sitemap_elem in sitemap_elems:
                # Try both namespaced and non-namespaced loc elements
                loc_elem = sitemap_elem.find("sitemap:loc", SITEMAP_NS)
                if loc_elem is None:
                    loc_elem = sitemap_elem.find("loc")
                
                if loc_elem is not None and loc_elem.text:
                    sitemap_urls.append(loc_elem.text.strip())
                    logger.debug(f"Found sitemap in index: {loc_elem.text.strip()}")
        
        return sitemap_urls
    except Exception as e:
        logger.error(f"Error parsing sitemap index {sitemap_url}: {e}")
        return []


def parse_sitemap(sitemap_url: str, base_url: str = None) -> List[Tuple[str, Optional[datetime]]]:
    """
    Parse a sitemap XML file and extract all URLs with their lastmod dates
    
    Args:
        sitemap_url: URL to sitemap XML file
        base_url: Base URL for resolving relative URLs (optional)
    
    Returns:
        List of tuples: (url, lastmod_date) where lastmod_date can be None
    """
    urls_with_dates = []
    try:
        session = create_session_with_retry()
        response = session.get(sitemap_url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (compatible; SiteBuilderBot/1.0)"
        })
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        
        # Check if it's a sitemap index
        if root.tag.endswith("sitemapindex"):
            logger.info(f"Sitemap {sitemap_url} is a sitemap index, fetching individual sitemaps...")
            sitemap_urls = parse_sitemap_index(sitemap_url)
            for sub_sitemap_url in sitemap_urls:
                sub_urls = parse_sitemap(sub_sitemap_url, base_url)
                urls_with_dates.extend(sub_urls)
            return urls_with_dates
        
        # Parse regular sitemap
        # Try namespaced first (standard sitemap format)
        url_elems = root.findall(".//sitemap:url", SITEMAP_NS)
        if not url_elems:
            # Fallback: try without namespace (some sitemaps don't use namespaces)
            url_elems = root.findall(".//url")
        
        for url_elem in url_elems:
            # Try both namespaced and non-namespaced loc elements
            loc_elem = url_elem.find("sitemap:loc", SITEMAP_NS)
            if loc_elem is None:
                loc_elem = url_elem.find("loc")
            
            if loc_elem is not None and loc_elem.text:
                url = loc_elem.text.strip()
                # Resolve relative URLs if base_url provided
                if base_url and not url.startswith("http"):
                    url = urljoin(base_url, url)
                
                # Try to extract lastmod date
                lastmod_date = None
                lastmod_elem = url_elem.find("sitemap:lastmod", SITEMAP_NS)
                if lastmod_elem is None:
                    lastmod_elem = url_elem.find("lastmod")
                
                if lastmod_elem is not None and lastmod_elem.text:
                    try:
                        # Parse ISO 8601 date format (e.g., "2025-11-18T04:18:32+00:00" or "2025-11-18")
                        date_str = lastmod_elem.text.strip()
                        # Try full ISO format first
                        try:
                            lastmod_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        except ValueError:
                            # Try date-only format
                            try:
                                lastmod_date = datetime.strptime(date_str.split('T')[0], '%Y-%m-%d')
                            except ValueError:
                                logger.debug(f"Could not parse date: {date_str}")
                    except Exception as e:
                        logger.debug(f"Error parsing lastmod date for {url}: {e}")
                
                urls_with_dates.append((url, lastmod_date))
        
        logger.info(f"Parsed {len(urls_with_dates)} URLs from sitemap {sitemap_url}")
        return urls_with_dates
    
    except ET.ParseError as e:
        logger.error(f"XML parse error for {sitemap_url}: {e}")
        return []
    except requests.RequestException as e:
        logger.error(f"Request error fetching {sitemap_url}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error parsing sitemap {sitemap_url}: {e}")
        return []


def parse_sitemap_from_site(site_url: str, max_urls: int = 1000, most_recent: Optional[int] = None) -> List[str]:
    """
    Main function to parse sitemap from a website
    
    Attempts multiple strategies:
    1. Try common sitemap URLs (sitemap.xml, sitemap_index.xml)
    2. Check robots.txt for sitemap location
    3. Parse sitemap index if found
    4. Parse individual sitemaps
    
    Args:
        site_url: Base URL of the website
        max_urls: Maximum number of URLs to return (for performance)
        most_recent: If provided, return only the N most recent URLs based on lastmod date
    
    Returns:
        List of URLs found in the sitemap(s), optionally filtered by date
    """
    try:
        # Normalize the site URL
        site_url = site_url.strip().rstrip("/")
        
        # Validate URL format
        if not site_url.startswith(("http://", "https://")):
            logger.error(f"❌ Invalid URL format: {site_url}. Must start with http:// or https://")
            return []
        
        parsed_base = urlparse(site_url)
        if not parsed_base.netloc:
            logger.error(f"❌ Invalid URL: {site_url}. Missing domain name.")
            return []
        
        base_url = f"{parsed_base.scheme}://{parsed_base.netloc}"
        logger.info(f"🔍 Auto-discovering sitemap for site: {base_url} (from input: {site_url})")
        logger.info(f"🔍 Will try common sitemap locations and robots.txt to find sitemap automatically")
        
        all_urls_with_dates: List[Tuple[str, Optional[datetime]]] = []
        errors_encountered = []
        
        # Strategy 1: Try common sitemap URLs (auto-discovery)
        potential_sitemaps = find_sitemap_urls(base_url)
        logger.info(f"🔍 Trying {len(potential_sitemaps)} potential sitemap locations: {potential_sitemaps[:3]}...")
        
        for sitemap_url in potential_sitemaps:
            if len(all_urls_with_dates) >= max_urls * 2:  # Collect more if we need to filter by date
                break
            
            try:
                # Check if it's robots.txt
                if "robots.txt" in sitemap_url:
                    logger.debug(f"🔍 Checking robots.txt: {sitemap_url}")
                    sitemap_urls_from_robots = get_sitemap_from_robots_txt(sitemap_url)
                    if sitemap_urls_from_robots:
                        logger.info(f"✅ Found {len(sitemap_urls_from_robots)} sitemap(s) in robots.txt")
                    for robots_sitemap_url in sitemap_urls_from_robots:
                        urls_with_dates = parse_sitemap(robots_sitemap_url, base_url)
                        all_urls_with_dates.extend(urls_with_dates)
                        if len(all_urls_with_dates) >= max_urls * 2:
                            break
                else:
                    logger.debug(f"🔍 Trying sitemap: {sitemap_url}")
                    urls_with_dates = parse_sitemap(sitemap_url, base_url)
                    all_urls_with_dates.extend(urls_with_dates)
                    if urls_with_dates:
                        logger.info(f"✅ Successfully parsed sitemap from {sitemap_url}, found {len(urls_with_dates)} URLs")
                        # If we found URLs, we can stop trying other locations
                        if len(all_urls_with_dates) >= 10:  # Found at least some URLs
                            break
            except Exception as e:
                error_msg = f"Failed to parse {sitemap_url}: {str(e)}"
                logger.warning(f"⚠️ {error_msg}")
                errors_encountered.append(error_msg)
                continue
        
        # Filter URLs to only include same domain
        base_domain = parsed_base.netloc
        filtered_urls_with_dates = []
        
        for url, date in all_urls_with_dates:
            try:
                parsed = urlparse(url)
                if parsed.netloc == base_domain or parsed.netloc == "":
                    filtered_urls_with_dates.append((url, date))
            except Exception:
                continue
        
        # If most_recent is specified, sort by date and take only the most recent N
        if most_recent and most_recent > 0:
            logger.info(f"📅 Filtering to {most_recent} most recent URLs based on lastmod date...")
            # Sort by date (most recent first), URLs without dates go to the end
            filtered_urls_with_dates.sort(key=lambda x: (x[1] is None, x[1] or datetime.min), reverse=True)
            filtered_urls_with_dates = filtered_urls_with_dates[:most_recent]
            urls_with_dates = len([d for d in filtered_urls_with_dates if d[1] is not None])
            logger.info(f"✅ Selected {most_recent} most recent URLs ({urls_with_dates} with dates, {most_recent - urls_with_dates} without dates)")
        
        # Extract just the URLs
        filtered_urls = [url for url, _ in filtered_urls_with_dates]
        
        # Apply max_urls limit
        if len(filtered_urls) > max_urls:
            filtered_urls = filtered_urls[:max_urls]
        
        if filtered_urls:
            logger.info(f"✅ Total URLs extracted from {site_url}: {len(filtered_urls)}")
        else:
            logger.warning(f"⚠️ No URLs extracted from {site_url}")
            if errors_encountered:
                logger.warning(f"⚠️ Errors encountered: {errors_encountered[:3]}")
            logger.warning(f"⚠️ Tried sitemap locations: {potential_sitemaps}")
        
        return filtered_urls
    except Exception as e:
        logger.error(f"❌ Critical error in parse_sitemap_from_site for {site_url}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


if __name__ == "__main__":
    # Test the parser
    import sys
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        urls = parse_sitemap_from_site(test_url)
        print(f"\nFound {len(urls)} URLs:")
        for url in urls[:20]:  # Show first 20
            print(f"  - {url}")
        if len(urls) > 20:
            print(f"  ... and {len(urls) - 20} more")

