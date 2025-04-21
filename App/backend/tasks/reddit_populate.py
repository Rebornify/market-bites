from modules.reddit_fetcher import fetch_hot_posts, AVAILABLE_SUBREDDITS
from reddit_worker import process_reddit_queue

for sub in AVAILABLE_SUBREDDITS:
    fetch_hot_posts(subreddit=sub,posts=10)
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

