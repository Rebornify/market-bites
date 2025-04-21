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
        print(f"Processing: {article['title']}")

        full_text = f"{article['title']} {article['content']}".strip()

        # NLP processing
        sentiment = analyzer.analyze(full_text)
        topics = topicModel.extract_topics(full_text)
        summary = summarizer.summarize(article['content'])
        named_entities = ner_model.extract_entities(article["title"], summary)

        # Save analysis result
        result_doc = {
            "post_id": article["link"],
            "title": article["title"],
            "source": article["source"],
            "content": article["content"],
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

        # Avoid duplicate results + don't add empty summaries
        if result_doc["summary"] != "":
            news_collection.update_one(
                {"post_id": article["link"]},  # Match by post_id
                {"$set": result_doc},          # Update with new content
                upsert=True                    # Insert if not found
            )

    print("Queue processed and stored in MongoDB.")
