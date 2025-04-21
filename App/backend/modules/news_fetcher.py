import os
from finlight_client import FinlightApi
from queue import Queue
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Temporary in-memory queue (replace with Redis or DB in production)
processing_queue = Queue()
FINLIGHT_API_KEY = os.getenv("FINLIGHT_API_KEY")

config = {
    "api_key": FINLIGHT_API_KEY,
}

client = FinlightApi(config)

def fetch_news_to_queue(query: str, page: int = 1, pageSize: int = 1, return_raw=False):
    print(f"Fetching news for query: {query}, page: {page}")
    response = client.articles.get_extended_articles({
        "query": query,
        "pageSize": pageSize,
        "page": page,
        "order": "DESC"
    })

    if response.get("status") != "ok":
        print("Invalid API response:", response)
        return [] if return_raw else None

    articles = []

    for article in response["articles"]:
        item = {
            "post_id": article["link"],  # Used in MongoDB for dedup
            "title": article["title"],
            "content": article.get("content", ""),
            "summary": article.get("summary"),
            "link": article["link"],
            "publishDate": article.get("publishDate").isoformat().replace("+00:00", "Z"),
            "source": article.get("source", "Unknown"),
        }

        if return_raw:
            articles.append(item)
        else:
            processing_queue.put(item)
            print(f"Queued: {item['title']}")

    return articles if return_raw else None