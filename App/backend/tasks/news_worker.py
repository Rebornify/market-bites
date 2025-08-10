from datetime import datetime
from pymongo import MongoClient
from modules.sentiment_analyzer import SentimentAnalyzer
from modules.news_topic_modeler import NewsTopicModeler
from modules.ner_analyzer_news import NERNewsModel
from modules.news_fetcher import processing_queue
import os

# MongoDB Setup
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["financial_data"]
news_collection = db["news_data"]


# Instance of Models - removed TextSummarizer since we use API summary
analyzer = SentimentAnalyzer() 
topicModel = NewsTopicModeler()
ner_model = NERNewsModel()


def process_news_queue():
    while not processing_queue.empty():
        article = processing_queue.get()
        title = article.get('title', '').strip()
        summary = article.get('summary', '').strip()
        
        # Validate title and summary
        if not title:
            print(f"Skipping article due to missing title")
            continue
            
        # Since we don't have content on free tier, validate based on summary
        # Be more lenient with summary length since API summaries may be shorter
        if not summary or len(summary) < 10:
            print(f"Skipping article due to insufficient summary: {title}")
            continue

        # Check if the article has already been processed using its link as post_id
        if news_collection.find_one({"post_id": article["link"]}):
            print(f"Skipping already processed article: {title}")
            continue

        print(f"Processing: {title}")

        # For NLP processing, use title + summary as the full text since content isn't available
        full_text = f"{title} {summary}".strip()

        # Use API-provided sentiment if available, otherwise analyze ourselves
        if article.get('sentiment') and article.get('confidence'):
            sentiment = {
                "score": 0.0,  # API doesn't provide score, set to neutral
                "sentiment": article.get('sentiment', 'neutral'),
                "confidence": article.get('confidence', 0.0)
            }
        else:
            # Fallback to our sentiment analyzer if API doesn't provide sentiment
            sentiment = analyzer.analyze(full_text)

        # Extract topics from title + summary
        topics = topicModel.extract_topics(full_text)
        
        # Use API-provided summary directly
        api_summary = summary
        
        # Extract named entities from title and summary
        named_entities = ner_model.extract_entities(title, api_summary)

        # Save analysis result
        result_doc = {
            "post_id": article["link"],
            "title": title,
            "source": article.get("source", "Unknown"),
            "content": "",  # No content available on free tier
            "link": article["link"],
            "sentiment": {"score": sentiment["score"], 
                          "label": sentiment["sentiment"], 
                          "confidence": sentiment["confidence"]},
            "topics": topics, # array e.g. [0: "topic", 1: "topic1"]
            "ner_results": named_entities,
            "summary": api_summary,  # Use API-provided summary
            "publishDate": article["publishDate"],
            "language": article.get("language", "en"),
            "images": article.get("images", []),
            "processed_at": datetime.now()
        }

        # Upsert the document, ensuring it's stored even if the summary is empty.
        news_collection.update_one(
            {"post_id": article["link"]},  # Match by post_id
            {"$set": result_doc},          # Update with new content
            upsert=True                    # Insert if not found
        )

    print("Queue processed and stored in MongoDB.")
