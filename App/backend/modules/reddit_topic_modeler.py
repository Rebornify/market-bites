import os
import re
import html
import contractions
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
from nltk import pos_tag
from gensim.corpora.dictionary import Dictionary
from gensim.models import Nmf, TfidfModel

class RedditTopicModeler:
    def __init__(self, model_dir=None):
        if model_dir is None:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_dir = os.path.join(base_path, 'models', 'nmf_reddit')

        print(f"Loading Reddit topic model from: {model_dir}")

        self.topic_labels = {
            1: "Reddit Governance & Moons",
            2: "Market ETFs & Index Trading",
            3: "Geopolitics: Oil & Energy",
            4: "Inflation & Fed Policy",
            5: "Options Mechanics (Calls, Puts)",
            6: "Crypto Trading & Sentiment",
            7: "Crypto Tech & Transactions",
            8: "Tesla, Musk & Investors",
            9: "Crypto Payments & Loans",
            10: "Options Strategy & Learning",
            11: "US & Global Economic News",
            12: "Stock Investing (Dividends, Growth)",
            13: "Earnings Reports & Forecasts",
            14: "Investment Basics & Valuation",
            15: "Reddit Rules & Trading Schemes",
            16: "Meme Stocks & Squeezes (GME, AMC)",
            17: "Options Volatility (IV, VIX)",
            18: "Investment Strategy & Advice",
            19: "Trading Predictions & Platforms"
        }
        self.incoherent_indices = {14, 18}  # 0-based indices

        self.lemmatizer = WordNetLemmatizer()
        self.stopwords = self._get_custom_stopwords()

        self.nmf_model = Nmf.load(os.path.join(model_dir, 'gensim_nmf_tfidf.model'))
        self.dictionary = Dictionary.load(os.path.join(model_dir, 'gensim_dictionary.dict'))
        self.tfidf_model = TfidfModel.load(os.path.join(model_dir, 'gensim_tfidf.model'))

    def _get_custom_stopwords(self):
        default = set(stopwords.words('english'))
        additional = {
            'also', 'anyone', 'back', 'bad', 'check', 'come', 'content', 'could', 'everyone', 'even',
            'every', 'feel', 'find', 'get', 'give', 'go', 'good', 'great', 'group', 'guy',
            'important', 'keep', 'know', 'let', 'like', 'look', 'lot', 'make', 'many', 'may',
            'much', 'must', 'never', 'new', 'number', 'one', 'part', 'people', 'really',
            'result', 'right', 'say', 'see', 'seem', 'something', 'still', 'thing', 'think',
            'try', 'use', 'video', 'want', 'way', 'well', 'would', 'click', 'comment',
            'disclaimer', 'discussion', 'edit', 'general', 'information', 'karma', 'link',
            'list', 'meta', 'mod', 'op', 'poll', 'post', 'prior', 'read', 'reddit', 'rule',
            'share', 'sub', 'subreddit', 'thread', 'topic', 'user', 'welcome', 'please',
            'currently', 'daily', 'day', 'et', 'friday', 'january', 'last', 'month', 'monthly', 'pm',
            'recent', 'since', 'time', 'today', 'tomorrow', 'week', 'year', 'yesterday',
            'account', 'around', 'article', 'data', 'different', 'example', 'move', 'need', 'pay',
            'project', 'start', 'take', 'work', 'average', 'big', 'high', 'low', 'max', 'medium',
            'answer', 'ask', 'help', 'hi', 'live', 'open', 'question', 'talk', 'tell', 'you',
            'com', 'dot', 'free', 'inc'
        }
        default.update(additional)
        return default

    def preprocess(self, text):
        def remove_markdown(t):
            t = re.sub(r'\*\*(.*?)\*\*', r'\1', t)
            t = re.sub(r'__(.*?)__', r'\1', t)
            t = re.sub(r'\*(.*?)\*', r'\1', t)
            t = re.sub(r'_(.*?)_', r'\1', t)
            t = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', t)
            t = re.sub(r'`{1,3}(.*?)`{1,3}', r'\1', t)
            return t

        us_placeholder = "__US_PLACEHOLDER__"
        text = re.sub(r'<.*?>', '', text)
        text = html.unescape(text)
        text = html.unescape(text)
        text = re.sub(r'\b[/\\\\]?[ur]/\w+\b', '', text)
        text = remove_markdown(text)
        text = re.sub(r'http\S+|www\.\S+', '', text)
        text = re.sub(r'U\\.S\\.', us_placeholder, text, flags=re.IGNORECASE)
        text = re.sub(r'\bUS\b', us_placeholder, text)
        try:
            text = contractions.fix(text)
        except Exception:
            pass
        text = re.sub(r'\\n+|\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        text = text.replace(us_placeholder, "U.S.")

        # Tokenization & Lemmatization
        tokens = word_tokenize(text)
        tagged = pos_tag(tokens)

        def get_wordnet_pos(treebank_tag):
            if treebank_tag.startswith('J'): return wordnet.ADJ
            elif treebank_tag.startswith('V'): return wordnet.VERB
            elif treebank_tag.startswith('N'): return wordnet.NOUN
            elif treebank_tag.startswith('R'): return wordnet.ADV
            return wordnet.NOUN

        def resolve_us_token(token, pos):
            if pos in ["NNP", "NNPS"] and token.lower() in ["us", "u.s.", "u.s"]:
                return "united_states"
            return token

        lemmas = [self.lemmatizer.lemmatize(resolve_us_token(token, pos), get_wordnet_pos(pos)).lower() for token, pos in tagged]

        numeric_pattern = re.compile(r'^\s*[+-]?(\d{1,3}(?:[.,]\d{3})*|\d+)(?:[.,]\d+)?\s*$')
        punctuation_artifacts = {"''", "'s", "``", "--", "-", "\\-", "...", "`", "p."}

        cleaned_tokens = [t for t in lemmas if t not in self.stopwords and len(t) > 1 and re.search(r'\w', t) and not numeric_pattern.fullmatch(t) and t not in punctuation_artifacts]
        return cleaned_tokens

    def extract_topics(self, text):
        try:
            print("Preprocessing for topic modeling...")
            tokens = self.preprocess(text)
            bow = self.dictionary.doc2bow(tokens)
            print("Extracting topics...")
            tfidf = self.tfidf_model[bow]
            dist = self.nmf_model[tfidf]

            sorted_topics = sorted(dist, key=lambda x: x[1], reverse=True)

            top_coherent_topics = []
            for topic_idx, score in sorted_topics:
                if topic_idx not in self.incoherent_indices:
                    label = self.topic_labels.get(topic_idx + 1, f"Unknown Topic {topic_idx + 1}")
                    top_coherent_topics.append({
                        "name": label,
                        "score": round(score, 4)
                    })
                    if len(top_coherent_topics) == 2:
                        break
            return top_coherent_topics
        
        except Exception as e:
            print(f"Error during Reddit topic modeling: {e}")
            return []
