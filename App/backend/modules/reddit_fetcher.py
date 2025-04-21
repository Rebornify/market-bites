import praw
import os
from datetime import datetime, timezone

AVAILABLE_SUBREDDITS = [
    'StockMarket', 'stocks', 'ValueInvesting', 'Options',
    'investing', 'CryptoCurrency', 'Bogleheads'
]
DEFAULT_SUBREDDIT = 'stocks'

# PRAW Setup using environment variables
try:
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=f'python:market-bites-app:v1.0 (by /u/{os.getenv("REDDIT_USERNAME")})',
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD")
    )
    # Test authentication (optional but good)
    print(f"PRAW instance created successfully. Authenticated as: {reddit.user.me()}")
except Exception as e:
    print(f"ERROR: Failed to create PRAW instance or authenticate: {e}")
    reddit = None

def fetch_hot_posts_praw(subreddit=DEFAULT_SUBREDDIT, posts: int = 0):
    """Fetches hot posts from a given subreddit using PRAW."""
    if reddit is None:
        print("ERROR: PRAW instance not available.")
        return []

    if subreddit not in AVAILABLE_SUBREDDITS:
        print(f"ERROR: Subreddit '{subreddit}' is not supported.")
        return []

    found_posts = []
    try:
        print(f"Fetching {posts} hot posts from r/{subreddit} using PRAW...")
        subreddit_instance = reddit.subreddit(subreddit)

        for submission in subreddit_instance.hot(limit=posts):
            # Convert PRAW submission object to dictionary format expected by frontend/serializer
            post = {
                # Use 'id' directly if serialize_doc handles it, otherwise keep post_id
                "post_id": submission.id,
                "title": submission.title,
                "selftext": submission.selftext,
                "score": submission.score,
                "url": submission.url, # External URL if not a self post
                "link": f"https://www.reddit.com{submission.permalink}", # Consistent field name for reddit link
                "publishDate": datetime.fromtimestamp(submission.created_utc, tz=timezone.utc).isoformat().replace("+00:00", "Z"), # For sorting/display
                "num_comments": submission.num_comments,
                "source": str(submission.author) if submission.author else "[deleted]", # Use 'source' field name like news_fetcher
                "is_self": submission.is_self,
                "subreddit": str(submission.subreddit),
                # Add other fields if your frontend/serializer expects them
                # "ner_results": [], # Placeholder if needed downstream
                # "topics": [], # Placeholder if needed downstream
                # "sentiment": {} # Placeholder if needed downstream
            }
            found_posts.append(post)

        print(f"Successfully fetched {len(found_posts)} posts via PRAW from r/{subreddit}")
        return found_posts

    except Exception as e:
        print(f"ERROR fetching/processing Reddit posts via PRAW for r/{subreddit}: {e}")
        return [] # Return empty list on error
