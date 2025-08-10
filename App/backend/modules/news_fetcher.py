import os
import requests
from queue import Queue
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Temporary in-memory queue (replace with Redis or DB in production)
processing_queue = Queue()
FINLIGHT_API_KEY = os.getenv("FINLIGHT_API_KEY")

# Finlight API v2 configuration
FINLIGHT_API_BASE_URL = "https://api.finlight.me/v2"

def fetch_news_to_queue(query: str, page: int = 1, pageSize: int = 1, return_raw=False):
    """
    Fetch news articles from Finlight API v2.
    Uses the new POST /v2/articles endpoint with direct HTTP requests.
    """
    print(f"Fetching news for query: {query}, page: {page}")
    
    if not FINLIGHT_API_KEY:
        print("ERROR: FINLIGHT_API_KEY not set in environment variables")
        return [] if return_raw else None

    # Prepare the request
    url = f"{FINLIGHT_API_BASE_URL}/articles"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "X-API-KEY": FINLIGHT_API_KEY
    }
    
    # Request body for v2 API
    request_body = {
        "query": query,
        "pageSize": pageSize,
        "page": page,
        "order": "DESC",
        # Don't request content since it's not available on free tier
        "includeContent": False,
        # Don't request entities since it's not available on free tier  
        "includeEntities": False
    }

    try:
        response = requests.post(url, headers=headers, json=request_body, timeout=30)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        
        data = response.json()
        
        if data.get("status") != "ok":
            print(f"Invalid API response status: {data.get('status')}")
            return [] if return_raw else None

        articles = []

        for article in data.get("articles", []):
            # Parse publishDate string to datetime object, then format consistently
            publish_date_str = article.get("publishDate")
            if publish_date_str:
                try:
                    # Handle ISO date string format
                    if publish_date_str.endswith('Z'):
                        publish_date_formatted = publish_date_str
                    else:
                        # Parse and reformat to ensure consistency
                        dt = datetime.fromisoformat(publish_date_str.replace('Z', '+00:00'))
                        publish_date_formatted = dt.isoformat().replace("+00:00", "Z")
                except (ValueError, AttributeError) as e:
                    print(f"Warning: Could not parse publishDate '{publish_date_str}': {e}")
                    publish_date_formatted = publish_date_str
            else:
                publish_date_formatted = datetime.now().isoformat().replace("+00:00", "Z")

            item = {
                "post_id": article["link"],  # Used in MongoDB for dedup
                "title": article["title"],
                "content": "",  # Content not available on free tier
                "summary": article.get("summary", ""),  # Use API-provided summary
                "link": article["link"],
                "publishDate": publish_date_formatted,
                "source": article.get("source", "Unknown"),
                "sentiment": article.get("sentiment", "neutral"),  # API provides sentiment
                "confidence": article.get("confidence", 0.0),  # API provides confidence
                "language": article.get("language", "en"),
                "images": article.get("images", [])
            }

            if return_raw:
                articles.append(item)
            else:
                processing_queue.put(item)
                print(f"Queued: {item['title']}")

        print(f"Successfully fetched {len(articles)} articles")
        return articles if return_raw else None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching news from Finlight API: {e}")
        return [] if return_raw else None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return [] if return_raw else None