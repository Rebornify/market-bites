# import schedule
# import time
# import random
from modules.news_fetcher import fetch_news_to_queue
from news_worker import process_news_queue

COMPANY_QUERIES = [
    "Apple", "Google", "Microsoft", "Tesla", "Amazon",
    "Nvidia", "Meta", "Netflix", "Intel", "JP Morgan",
    "Goldman Sachs", "Alibaba", "Samsung", "AMD", "Boeing",
    "Deepseek", "OpenAI"
]

for company in COMPANY_QUERIES:
    print("Populating database for: ", company)
    fetch_news_to_queue(company, 10)
    process_news_queue()

# def scheduled_news_job():
#     query = random.choice(COMPANY_QUERIES)
#     print(f"Running scheduled job for query: {query}")
#     fetch_news_to_queue(query)
#     # fetch_news_to_queue("") # just get any news
#     process_news_queue()

# schedule.every(30).minutes.do(scheduled_news_job)

# print("News Scheduler started. Press Ctrl+C to stop.")
# while True:
#     schedule.run_pending()
#     time.sleep(1)
