from typing import List, Optional

def format_task_from_urls(urls: List[str], query: str) -> str:
    url_block = "\n".join(urls)
    return f"{url_block}\n\nTask: {query}"


def process_tweets(data):
    """Process the API response to extract tweet text."""
    filtered_tweets = []
    for tweet in data.get("timeline", []):
        if tweet.get("type") == "tweet":
            tweet_text = tweet.get("text", "")
            filtered_tweets.append({
                "text": tweet_text
            })
    return filtered_tweets