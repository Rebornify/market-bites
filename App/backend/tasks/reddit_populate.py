from modules.reddit_fetcher import fetch_hot_posts_praw, AVAILABLE_SUBREDDITS
from reddit_worker import process_reddit_queue
from pymongo import MongoClient
import sys
import os
from dotenv import load_dotenv

for sub in AVAILABLE_SUBREDDITS:
    fetch_hot_posts_praw(subreddit=sub, posts=10)
    print("Fetched for: ", sub)

print("Processing queue...")
process_reddit_queue()

# reddit_scheduler.py

# import schedule
# import time
# from modules.reddit_fetcher import fetch_hot_posts, AVAILABLE_SUBREDDITS
# from reddit_worker import process_reddit_queue

# def job():
#     print("Fetching and processing Reddit posts...")
#     for sub in AVAILABLE_SUBREDDITS:
#         fetch_hot_posts(subreddit=sub)
#     process_reddit_queue()
#     print("Done.\n")

# # Schedule the job every 30 minutes
# schedule.every(30).minutes.do(job)

# # Run immediately on start (optional)
# job()

# print("Reddit fetch scheduler started. Running every 30 minutes...\n")

# # Keep running the scheduler
# while True:
#     schedule.run_pending()
#     time.sleep(1)

def populate_historic_posts(subreddit, limit=100):
    """
    Fetches hot posts from a subreddit and processes them,
    storing the results in MongoDB.
    """
    print(f"Fetching and processing {limit} hot posts from r/{subreddit}...")
    
    # Step 1: Fetch posts directly.
    posts = fetch_hot_posts_praw(subreddit=subreddit, posts=limit)
    
    # Step 2: Pass the list of posts to the worker.
    if posts:
        process_reddit_queue(posts)
    
    print(f"Finished populating historic posts for r/{subreddit}.")

if __name__ == "__main__":
    for sub in AVAILABLE_SUBREDDITS:
        populate_historic_posts(sub, limit=500) # Fetch more posts for historic data
    print("All subreddits have been populated.")

