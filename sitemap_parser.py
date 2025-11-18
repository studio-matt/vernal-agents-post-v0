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


def validate_url_format(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format and basic structure
    
    Args:
        url: URL string to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url or not isinstance(url, str):
        return False, "URL is empty or not a string"
    
    url = url.strip()
    if not url:
        return False, "URL is empty or whitespace only"
    
    # Check for protocol
    if not url.startswith(("http://", "https://")):
        return False, "URL must start with http:// or https://"
    
    # Parse URL
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return False, "URL is missing domain name"
        
        # Check for valid domain characters
        if len(parsed.netloc) > 253:  # Max domain length
            return False, "Domain name is too long (max 253 characters)"
        
        # Check for invalid characters in domain
        if ' ' in parsed.netloc:
            return False, "Domain name contains spaces"
        
        return True, None
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"


def validate_url_accessibility(url: str, timeout: int = 10) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Validate that a URL is accessible (DNS resolution, connectivity, HTTP status)
    
    Args:
        url: URL to validate
        timeout: Request timeout in seconds
    
    Returns:
        Tuple of (is_accessible, error_message, http_status_code)
        http_status_code will be None if request failed before getting a response
    """
    try:
        session = create_session_with_retry()
        response = session.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SiteBuilderBot/1.0)"},
            allow_redirects=True
        )
        status_code = response.status_code
        
        # Consider 2xx and 3xx as accessible (even if redirected)
        if 200 <= status_code < 400:
            return True, None, status_code
        elif status_code == 404:
            return False, f"Site returned 404 Not Found - the URL does not exist", status_code
        elif status_code == 403:
            return False, f"Site returned 403 Forbidden - access denied", status_code
        elif status_code == 503:
            return False, f"Site returned 503 Service Unavailable - server is down", status_code
        else:
            return False, f"Site returned HTTP {status_code}", status_code
            
    except requests.exceptions.Timeout:
        return False, "Connection timeout - the site did not respond in time", None
    except requests.exceptions.ConnectionError as e:
        error_str = str(e).lower()
        if "dns" in error_str or "name resolution" in error_str:
            return False, "DNS resolution failed - domain name does not exist", None
        elif "refused" in error_str:
            return False, "Connection refused - the server is not accepting connections", None
        else:
            return False, f"Connection error: {str(e)}", None
    except requests.exceptions.TooManyRedirects:
        return False, "Too many redirects - the URL redirects in a loop", None
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def quick_sitemap_check(site_url: str, timeout: int = 10) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Quickly check if a sitemap exists for the given site URL
    This is a lightweight check to fail early at initialization
    
    Args:
        site_url: Base URL of the website
        timeout: Request timeout in seconds
    
    Returns:
        Tuple of (sitemap_found, sitemap_url, error_message)
        sitemap_url will be None if not found
    """
    try:
        # Normalize URL
        site_url = site_url.strip().rstrip("/")
        
        # Validate format first
        is_valid, format_error = validate_url_format(site_url)
        if not is_valid:
            return False, None, format_error
        
        parsed_base = urlparse(site_url)
        base_url = f"{parsed_base.scheme}://{parsed_base.netloc}"
        
        # Check site accessibility first
        is_accessible, access_error, status_code = validate_url_accessibility(base_url, timeout=timeout)
        if not is_accessible:
            return False, None, f"Site is not accessible: {access_error}"
        
        # Try the most common sitemap locations first
        potential_sitemaps = [
            f"{base_url}/sitemap.xml",
            f"{base_url}/sitemap_index.xml",
        ]
        
        session = create_session_with_retry()
        
        # Quick check: try sitemap.xml first (most common)
        for sitemap_url in potential_sitemaps[:1]:  # Only check first one for speed
            try:
                response = session.head(sitemap_url, timeout=timeout, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; SiteBuilderBot/1.0)"
                })
                if response.status_code == 200:
                    # Verify it's actually XML
                    content_type = response.headers.get('Content-Type', '').lower()
                    if 'xml' in content_type:
                        return True, sitemap_url, None
            except requests.exceptions.RequestException:
                continue
        
        # If HEAD doesn't work, try robots.txt for sitemap location
        try:
            robots_url = f"{base_url}/robots.txt"
            response = session.get(robots_url, timeout=timeout, headers={
                "User-Agent": "Mozilla/5.0 (compatible; SiteBuilderBot/1.0)"
            })
            if response.status_code == 200:
                for line in response.text.split("\n"):
                    line = line.strip()
                    if line.lower().startswith("sitemap:"):
                        sitemap_url = line.split(":", 1)[1].strip()
                        # Quick check if this sitemap exists
                        try:
                            sitemap_response = session.head(sitemap_url, timeout=timeout, headers={
                                "User-Agent": "Mozilla/5.0 (compatible; SiteBuilderBot/1.0)"
                            })
                            if sitemap_response.status_code == 200:
                                return True, sitemap_url, None
                        except:
                            pass
        except:
            pass
        
        # If we get here, no sitemap was found in quick check
        # This doesn't mean it doesn't exist, but we'll let the full parse try
        return False, None, "Sitemap not found at common locations. Full parsing will attempt discovery."
        
    except Exception as e:
        logger.error(f"Error in quick_sitemap_check: {e}")
        return False, None, f"Error checking for sitemap: {str(e)}"


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
        logger.info(f"🔍 Base domain: {parsed_base.netloc}, Scheme: {parsed_base.scheme}")
        
        all_urls_with_dates: List[Tuple[str, Optional[datetime]]] = []
        errors_encountered = []
        
        # Strategy 1: Try common sitemap URLs (auto-discovery)
        potential_sitemaps = find_sitemap_urls(base_url)
        logger.info(f"🔍 Trying {len(potential_sitemaps)} potential sitemap locations:")
        for i, sitemap_loc in enumerate(potential_sitemaps[:5], 1):
            logger.info(f"   [{i}] {sitemap_loc}")
        
        for sitemap_url in potential_sitemaps:
            if len(all_urls_with_dates) >= max_urls * 2:  # Collect more if we need to filter by date
                break
            
            try:
                # Check if it's robots.txt
                if "robots.txt" in sitemap_url:
                    logger.info(f"🔍 Checking robots.txt: {sitemap_url}")
                    sitemap_urls_from_robots = get_sitemap_from_robots_txt(sitemap_url)
                    if sitemap_urls_from_robots:
                        logger.info(f"✅ Found {len(sitemap_urls_from_robots)} sitemap(s) in robots.txt: {sitemap_urls_from_robots}")
                        for robots_sitemap_url in sitemap_urls_from_robots:
                            logger.info(f"🔍 Parsing sitemap from robots.txt: {robots_sitemap_url}")
                            urls_with_dates = parse_sitemap(robots_sitemap_url, base_url)
                            if urls_with_dates:
                                logger.info(f"✅ Parsed {len(urls_with_dates)} URLs from {robots_sitemap_url}")
                            all_urls_with_dates.extend(urls_with_dates)
                            if len(all_urls_with_dates) >= max_urls * 2:
                                break
                    else:
                        logger.debug(f"⚠️ No sitemap URLs found in robots.txt")
                else:
                    logger.info(f"🔍 Trying sitemap: {sitemap_url}")
                    urls_with_dates = parse_sitemap(sitemap_url, base_url)
                    if urls_with_dates:
                        logger.info(f"✅ Successfully parsed sitemap from {sitemap_url}, found {len(urls_with_dates)} URLs")
                        all_urls_with_dates.extend(urls_with_dates)
                        # If we found URLs, we can stop trying other locations
                        if len(all_urls_with_dates) >= 10:  # Found at least some URLs
                            logger.info(f"✅ Found sufficient URLs ({len(all_urls_with_dates)}), stopping search")
                            break
                    else:
                        logger.debug(f"⚠️ No URLs found in {sitemap_url} (may not exist or be empty)")
            except Exception as e:
                error_msg = f"Failed to parse {sitemap_url}: {str(e)}"
                logger.warning(f"⚠️ {error_msg}")
                errors_encountered.append(error_msg)
                continue
        
        # Filter URLs to only include same domain (but allow subdomains and relative URLs)
        base_domain = parsed_base.netloc
        # Extract root domain (e.g., "example.com" from "www.example.com" or "blog.example.com")
        base_domain_parts = base_domain.split('.')
        if len(base_domain_parts) >= 2:
            root_domain = '.'.join(base_domain_parts[-2:])  # Get last 2 parts (e.g., "example.com")
        else:
            root_domain = base_domain
        
        filtered_urls_with_dates = []
        filtered_out_count = 0
        
        for url, date in all_urls_with_dates:
            try:
                parsed = urlparse(url)
                # Allow: same domain, subdomains of same root, relative URLs, or empty netloc
                url_domain = parsed.netloc
                if not url_domain or url_domain == "":
                    # Relative URL - keep it
                    filtered_urls_with_dates.append((url, date))
                elif url_domain == base_domain:
                    # Exact match - keep it
                    filtered_urls_with_dates.append((url, date))
                elif url_domain.endswith('.' + root_domain) or url_domain == root_domain:
                    # Subdomain or root domain match - keep it
                    filtered_urls_with_dates.append((url, date))
                else:
                    # Different domain - filter it out
                    filtered_out_count += 1
                    logger.debug(f"🔍 Filtered out URL from different domain: {url} (domain: {url_domain}, expected: {base_domain})")
            except Exception as e:
                logger.warning(f"⚠️ Error parsing URL {url}: {e}")
                filtered_out_count += 1
                continue
        
        if filtered_out_count > 0:
            logger.info(f"🔍 Filtered out {filtered_out_count} URLs from different domains (kept {len(filtered_urls_with_dates)} URLs from {base_domain})")
        
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
            logger.info(f"✅ First 5 URLs: {filtered_urls[:5]}")
        else:
            logger.error(f"❌ No URLs extracted from {site_url}")
            logger.error(f"❌ Total URLs found before filtering: {len(all_urls_with_dates)}")
            logger.error(f"❌ URLs after domain filtering: {len(filtered_urls_with_dates)}")
            if errors_encountered:
                logger.error(f"❌ Errors encountered during parsing: {errors_encountered[:5]}")
            logger.error(f"❌ Tried sitemap locations: {potential_sitemaps}")
            # Log sample URLs that were found but filtered out
            if len(all_urls_with_dates) > 0:
                logger.error(f"❌ Sample URLs found (may have been filtered): {[url for url, _ in all_urls_with_dates[:5]]}")
        
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

