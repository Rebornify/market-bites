import schedule
import time
from modules.reddit_fetcher import fetch_hot_posts, AVAILABLE_SUBREDDITS
from reddit_worker import process_reddit_queue
from modules.news_fetcher import fetch_news_to_queue
from news_worker import process_news_queue

def fetch_latest():
    print("Fetching and processing Reddit posts...")
    for sub in AVAILABLE_SUBREDDITS:
        print("Subreddit: ", sub)
        fetch_hot_posts(subreddit=sub, posts=5)
    process_reddit_queue()
    print("Fetched and processed Reddit posts.\n")
    print()
    print("Fetching and processing 20 news articles...")
    fetch_news_to_queue("", pageSize=75)
    process_news_queue()
    print("News done yay wait another hour")

# Schedule the job every 30 minutes
schedule.every(1).hours.do(fetch_latest)

# Run immediately on start (optional)
fetch_latest()
print("Fetch scheduler started. Running every 1 hour...\n")

# Keep running the scheduler
while True:
    schedule.run_pending()
    time.sleep(1)