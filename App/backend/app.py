from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os

# Import the correct functions
from modules.news_fetcher import fetch_news_to_queue
from modules.reddit_fetcher import fetch_hot_posts_praw # Use PRAW function

# Load environment variables
load_dotenv()

app = Flask(__name__)
# app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'local-dev-secret-key-CHANGE-ME')

# Configure CORS using environment variable
frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
CORS(app, resources={r"/api/*": {"origins": frontend_url}})

# MongoDB Atlas connection
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("CRITICAL ERROR: MONGO_URI environment variable not set.")
    exit(1) # Exit if DB connection isn't possible

try:
    client = MongoClient(MONGO_URI)
    client.admin.command('ismaster') # Check connection
    print("MongoDB connection successful.")
    db = client["financial_data"]
    news_collection = db["news_data"]
    reddit_collection = db["reddit_data"]
except Exception as e:
    print(f"CRITICAL ERROR: Could not connect to MongoDB: {e}")
    exit(1)


def serialize_doc(doc):
    """Converts MongoDB doc (_id, dates) to JSON-serializable format."""
    if doc is None:
        return None
    # Handle potential ObjectId from DB if querying later
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    # Ensure key date fields are ISO strings if they are datetime objects
    for key in ["publishDate", "created_utc"]:
        if key in doc and isinstance(doc[key], datetime):
            doc[key] = doc[key].isoformat().replace("+00:00", "Z")
    return doc

@app.route('/api/news/search')
def search_news():
    print("/api/news/search triggered")
    query = request.args.get('query', '').lower()
    MIN_ARTICLES = 10 # Target minimum articles to return

    if not query:
        return jsonify([])

    # Step 1: Fetch identifiers (links) for potentially relevant fresh articles
    fresh_article_links = []
    try:
        fresh_news_info = fetch_news_to_queue(query, pageSize=20, return_raw=True)
        if fresh_news_info:
            # Use 'link' as the unique identifier stored as 'post_id' in the DB
            fresh_article_links = list(set([article['link'] for article in fresh_news_info if 'link' in article]))
            if fresh_article_links:
                 print(f"✅ Found {len(fresh_article_links)} unique potential article links for query '{query}'.")
            else:
                 print(f"⚠️ Could not extract links from fetch results for query: {query}")
        else:
             print(f"⚠️ No fresh news articles found via fetch for query: {query}")
             # Proceed to fallback if fetch returns None or empty

    except Exception as e:
        print(f"❌ Error during news fetch for query '{query}': {e}")
        # Allow fallback even if fetch fails

    processed_articles = []
    found_article_db_ids = set() # Track MongoDB '_id' (as 'id' string) to prevent duplicates

    # Step 2: Query DB for articles matching the fetched links
    if fresh_article_links:
        print(f"🔍 Querying DB for matches to {len(fresh_article_links)} links...")
        try:
            # Match based on 'post_id' which stores the article link
            results_cursor = news_collection.find({"post_id": {"$in": fresh_article_links}})
            initial_articles = [serialize_doc(doc) for doc in results_cursor]

            for article in initial_articles:
                # Ensure article is valid and we haven't added it already via another link (unlikely but safe)
                if article and article.get('id') not in found_article_db_ids:
                     processed_articles.append(article)
                     found_article_db_ids.add(article['id'])

            print(f"✅ Found {len(processed_articles)} articles in DB matching fresh links.")

        except Exception as e:
            print(f"❌ Database error querying news_collection for fresh links: {e}")
            # Allow fallback

    # Step 3: Fallback Query if not enough articles found yet
    num_found = len(processed_articles)
    if num_found < MIN_ARTICLES:
        needed = MIN_ARTICLES - num_found
        print(f"⚠️ Only found {num_found} matching fresh articles. Performing fallback query for {needed} more...")

        try:
            fallback_query_criteria = {
                # Exclude articles we already found via the link match
                # Note: We are comparing against the MongoDB '_id' (as 'id') here
                "id": {"$nin": list(found_article_db_ids)},
                # Match against NER results for relevance
                "ner_results": {
                    "$elemMatch": {
                        "text": {
                            "$regex": query,
                            "$options": "i" # Case-insensitive match
                        }
                    }
                }
            }
            # Sort by date within the fallback query, limit to needed amount
            fallback_cursor = news_collection.find(fallback_query_criteria).sort("publishDate", -1).limit(needed)
            fallback_articles = [serialize_doc(doc) for doc in fallback_cursor]

            # Add unique fallback articles (double check uniqueness based on 'id')
            for article in fallback_articles:
                 if article and article.get('id') not in found_article_db_ids:
                    processed_articles.append(article)
                    # No need to add to found_article_db_ids now, but good practice if logic changed
                    # found_article_db_ids.add(article['id'])

            print(f"✅ Added {len(fallback_articles)} articles from fallback query.")

        except Exception as e:
            print(f"❌ Database error during fallback query for '{query}': {e}")
            # Proceed with potentially fewer articles if fallback fails

    # Step 4: Final Sort and Return
    try:
        # Sort all collected articles (fresh matches + fallback) by publish date descending
        processed_articles.sort(key=lambda x: x.get("publishDate", ""), reverse=True)
        print(f"✅ Returning total {len(processed_articles)} articles for query '{query}'.")
        return jsonify(processed_articles)
    except Exception as e:
         print(f"❌ Error during final processing/sorting: {e}")
         return jsonify({"error": "Failed during final processing"}), 500

# --- Reddit Search Route (Using PRAW) ---
SUBREDDIT_MAP = {
    'stockmarket': 'StockMarket',
    'stocks': 'stocks',
    'valueinvesting': 'ValueInvesting',
    'options': 'Options',
    'investing': 'investing',
    'cryptocurrency': 'CryptoCurrency',
    'bogleheads': 'Bogleheads',
}

@app.route('/api/reddit/search')
def search_reddit():
    print("/api/reddit/search triggered")
    MIN_POSTS = 15 # Target minimum posts to return

    user_input = request.args.get('subreddit', 'stocks').lower()
    if user_input not in SUBREDDIT_MAP:
        return jsonify({"error": "Unsupported subreddit"}), 400

    subreddit = SUBREDDIT_MAP[user_input] # Use consistent casing for DB/PRAW
    print(f"✅ Subreddit selected: r/{subreddit}")

    # Step 1: Fetch identifiers (post IDs) for currently hot posts via PRAW
    fresh_post_ids = []
    try:
        limit = 20 # How many hot post IDs to attempt fetching
        fresh_posts_info = fetch_hot_posts_praw(subreddit=subreddit, posts=limit)
        if fresh_posts_info:
            fresh_post_ids = list(set([post['post_id'] for post in fresh_posts_info if 'post_id' in post]))
            if fresh_post_ids:
                print(f"✅ Found {len(fresh_post_ids)} unique hot post IDs via PRAW for r/{subreddit}.")
            else:
                 print(f"⚠️ Could not extract post IDs from PRAW fetch results for r/{subreddit}")
        else:
             print(f"⚠️ No fresh post info returned by PRAW fetch for r/{subreddit}")
             # Proceed to fallback if fetch returns None or empty

    except Exception as e:
        print(f"❌ Error during PRAW fetch for r/{subreddit}: {e}")
        # Allow fallback even if PRAW fails

    processed_posts = []
    found_reddit_post_ids = set() # Track the original Reddit post_id string

    # Step 2: Query DB for posts matching the fetched PRAW post IDs
    if fresh_post_ids:
        print(f"🔍 Querying DB for matches to {len(fresh_post_ids)} hot post IDs...")
        try:
            # Match based on the Reddit 'post_id' stored in the DB
            results_cursor = reddit_collection.find({"post_id": {"$in": fresh_post_ids}})
            # Sort initial matches by date here (optional, but can be slightly clearer)
            initial_posts = [serialize_doc(doc) for doc in results_cursor.sort("publishDate", -1)]

            for post in initial_posts:
                if post and post.get('id'): # Check if serialization worked
                    # Store the original Reddit post_id for the $nin filter in fallback
                    original_post_id = next((p['post_id'] for p in fresh_posts_info if post.get('id') == str(p.get('_id'))), None) # Re-find original id - slightly inefficient but safer if serialize_doc modified dict
                    # A better approach would be to ensure serialize_doc doesn't remove post_id OR pass post_id along
                    if original_post_id and original_post_id not in found_reddit_post_ids:
                         processed_posts.append(post)
                         found_reddit_post_ids.add(original_post_id)
                    elif not original_post_id and 'post_id' in post and post['post_id'] not in found_reddit_post_ids: # Fallback if post_id survived serialization
                        print(f"⚠️ Using post_id found directly in serialized doc for {post.get('id')}")
                        processed_posts.append(post)
                        found_reddit_post_ids.add(post['post_id'])
                    elif post.get('id'): # Only add if valid post and not already added
                        if post.get('id') not in [p.get('id') for p in processed_posts]: # Avoid duplicates by DB id if post_id missing
                             # This condition means we found the post by ID but couldn't track its original reddit post_id
                             print(f"⚠️ Warning: Could not reliably track original Reddit post_id for DB record {post.get('id')}. Adding post but fallback might refetch.")
                             processed_posts.append(post)


            print(f"✅ Found {len(processed_posts)} posts in DB matching hot IDs.")

        except Exception as e:
            print(f"❌ Database error querying reddit_collection for fresh post_ids: {e}")
            # Allow fallback

    # Step 3: Fallback Query if not enough posts found
    num_found = len(processed_posts)
    if num_found < MIN_POSTS:
        needed = MIN_POSTS - num_found
        print(f"⚠️ Only found {num_found} matching fresh posts. Performing fallback query for {needed} more...")

        try:
            fallback_query_criteria = {
                "subreddit": subreddit,
                # Exclude posts we already found via the PRAW ID match, using original Reddit IDs
                "post_id": {"$nin": list(found_reddit_post_ids)},
                # Add minimum score threshold for fallback results
                "score": {"$gt": 20}
            }
            # Find other posts from the same subreddit, sorted by date, excluding ones we already have
            fallback_cursor = reddit_collection.find(fallback_query_criteria).sort("publishDate", -1).limit(needed)
            fallback_posts = [serialize_doc(doc) for doc in fallback_cursor]

            # Extend the list with fallback results (no need to check uniqueness against found_reddit_post_ids due to $nin)
            processed_posts.extend(fallback_posts)

            print(f"✅ Added {len(fallback_posts)} posts from fallback query.")

        except Exception as e:
            print(f"❌ Database error during fallback query for r/{subreddit}: {e}")
            # Proceed with potentially fewer posts

    # Step 4: Final Sort and Return
    try:
        # Sort all collected posts (hot matches + fallback) by publish date descending
        processed_posts.sort(key=lambda x: x.get("publishDate", ""), reverse=True)
        print(f"✅ Returning total {len(processed_posts)} posts for r/{subreddit}.")
        return jsonify(processed_posts)
    except Exception as e:
        print(f"❌ Error during final processing/sorting for r/{subreddit}: {e}")
        return jsonify({"error": "Failed during final processing"}), 500

# --- Main Execution Block (For local dev via 'flask run') ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Debug mode controlled by FLASK_DEBUG env var when using 'flask run'
    app.run(host='0.0.0.0', port=port)
