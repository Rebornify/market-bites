# reddit_worker.py
from pymongo import MongoClient
from datetime import datetime
from modules.sentiment_analyzer import SentimentAnalyzer
from modules.reddit_topic_modeler import RedditTopicModeler
from modules.text_summarizer import TextSummarizer
from modules.ner_analyzer_reddit import NERRedditModel

import os
from dotenv import load_dotenv
from modules.reddit_fetcher import reddit_processing_queue

env_path = os.path.join(os.path.dirname(__file__), 'modules', '.env')
load_dotenv(dotenv_path=env_path)

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["financial_data"]
reddit_collection = db["reddit_data"]

analyzer = SentimentAnalyzer()
summarizer = TextSummarizer()
topicModel = RedditTopicModeler()
ner_model = NERRedditModel()


def process_reddit_queue():
    while not reddit_processing_queue.empty():
        post = reddit_processing_queue.get()
        print(f"Processing Reddit post: {post['title']}")

        full_text = f"{post['title']} {post['selftext']}".strip()

        sentiment = analyzer.analyze(full_text)
        topics = topicModel.extract_topics(full_text)
        summary = summarizer.summarize(post['selftext'])
        named_entities = ner_model.extract_entities(post["title"], summary)

        result_doc = {
            "post_id": post["post_id"],
            "title": post["title"],
            "source": post["author"],
            "content": post["selftext"],
            "link": post["redditUrl"],
            "sentiment": {"score": sentiment["score"], "label": sentiment["sentiment"], "confidence": sentiment["confidence"]},
            "topics": topics,
            "ner_results": named_entities,
            "summary": summary,
            "publishDate": post["created_utc"],
            "processed_at": datetime.now(),
            "subreddit": post["subreddit"],
            "score": post["score"],
            "num_comments": post["num_comments"]
        }

        # Avoid duplicate results + don't add empty summaries
        if result_doc["summary"] != "":
            reddit_collection.update_one(
                {"post_id": post["post_id"]},  # Match by post_id
                {"$set": result_doc},          # Update with new content
                upsert=True                    # Insert if not found
            )

    print("Reddit queue processed and stored in MongoDB.")
