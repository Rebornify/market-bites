from datetime import datetime
from pymongo import MongoClient
from modules.sentiment_analyzer import SentimentAnalyzer
from modules.text_summarizer import TextSummarizer
from modules.news_topic_modeler import NewsTopicModeler
from modules.ner_analyzer_news import NERNewsModel
from modules.news_fetcher import processing_queue
import os

# MongoDB Setup
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["financial_data"]
news_collection = db["news_data"]


# Instance of Models
analyzer = SentimentAnalyzer() 
topicModel = NewsTopicModeler()
ner_model = NERNewsModel()
summarizer = TextSummarizer()


def process_news_queue():
    while not processing_queue.empty():
        article = processing_queue.get()
        content = article.get('content', '').strip()
        title = article.get('title', '').strip()

        # --- Content Validation ---
        MIN_CONTENT_LENGTH = 150  # Characters
        BLOCKING_MESSAGE = "One of your browser extensions seems to be blocking the video player from loading"
        
        if not content or len(content) < MIN_CONTENT_LENGTH or BLOCKING_MESSAGE in content or content == title:
            print(f"Skipping article due to invalid/short content: {title}")
            continue

        # Check if the article has already been processed using its link as post_id
        if news_collection.find_one({"post_id": article["link"]}):
            print(f"Skipping already processed article: {title}")
            continue

        print(f"Processing: {title}")

        full_text = f"{title} {content}".strip()

        # NLP processing
        sentiment = analyzer.analyze(full_text)
        topics = topicModel.extract_topics(full_text)
        summary = summarizer.summarize(content, title=title)
        named_entities = ner_model.extract_entities(title, summary)

        # Save analysis result
        result_doc = {
            "post_id": article["link"],
            "title": title,
            "source": article["source"],
            "content": content,
            "link": article["link"],
            "sentiment": {"score": sentiment["score"], 
                          "label": sentiment["sentiment"], 
                          "confidence": sentiment["confidence"]},
            "topics": topics, # array e.g. [0: "topic", 1: "topic1"]
            "ner_results": named_entities,
            "summary": summary,
            "publishDate": article["publishDate"],
            "processed_at": datetime.now()
        }

        # Upsert the document, ensuring it's stored even if the summary is empty.
        news_collection.update_one(
            {"post_id": article["link"]},  # Match by post_id
            {"$set": result_doc},          # Update with new content
            upsert=True                    # Insert if not found
        )

    print("Queue processed and stored in MongoDB.")
