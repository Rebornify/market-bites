from dotenv import load_dotenv
load_dotenv() # Load environment variables from .env file

from modules.reddit_fetcher import fetch_hot_posts_praw, AVAILABLE_SUBREDDITS
from .reddit_worker import process_reddit_queue
from modules.news_fetcher import fetch_news_to_queue
from .news_worker import process_news_queue

def fetch_latest():
    print("Fetching and processing Reddit posts...")
    all_new_posts = []
    for sub in AVAILABLE_SUBREDDITS:
        print("Subreddit: ", sub)
        posts = fetch_hot_posts_praw(subreddit=sub, posts=5)
        if posts:
            all_new_posts.extend(posts)
    process_reddit_queue(all_new_posts)
    print("Fetched and processed Reddit posts.\n")
    print()
    print("Fetching and processing up to 50 news articles...")
    fetch_news_to_queue("finance OR stocks OR market OR earnings", pageSize=50)
    process_news_queue()
    print("News done yay wait another hour")

if __name__ == "__main__":
    fetch_latest()