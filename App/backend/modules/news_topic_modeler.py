import os
import re
import html
import contractions
from gensim.models import Nmf, TfidfModel
from gensim.corpora.dictionary import Dictionary
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
from nltk import pos_tag

class NewsTopicModeler:
    def __init__(self, model_path=None):
        """Initialize the topic modeling component.
        
        Args:
            model_path (str, optional): Path to the topic modeling model.
                                      If None, uses the default path in the backend directory.
        """
        # if model_path is None:
        #     # Get the absolute path to the backend directory
        #     backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        #     self.model_path = os.path.join(backend_dir, 'models', 'topic_model')
        # else:
        #     self.model_path = model_path
            
        # print(f"Topic model path set to: {self.model_path}")
        # TODO: Your team will implement the model loading here
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base_path = model_path or os.path.join(backend_dir, 'models', 'nmf_news')

        self.nmf_model_path = os.path.join(base_path, 'gensim_nmf_tfidf.model')
        self.dict_path = os.path.join(base_path, 'gensim_dictionary.dict')
        self.tfidf_model_path = os.path.join(base_path, 'gensim_tfidf.model')

        self.stopwords_set = set(stopwords.words('english'))
        self.lemmatizer = WordNetLemmatizer()

        self.topic_labels = {
            1: "Tesla & Electric Vehicles",
            2: "Earnings Estimates & Surprises",
            3: "Elon Musk & Twitter",
            4: "Quarterly Financial Results",
            5: "Banks, Interest Rates & Inflation",
            6: "Stock Market Movements",
            7: "Corporate Announcements",
            8: "Yahoo Finance & Earnings Coverage",
            9: "Big Tech & AI",
            10: "Healthcare & Pharmaceuticals",
            11: "Market Indices & Economic Data",
            12: "Earnings Calls & Executive Commentary",
            13: "Retail & Consumer Spending",
            14: "Analyst Insights & Investment Ideas",
            15: "Media & Streaming",
            16: "Auto Industry & Labor Strikes",
            17: "Costco & Wholesale Retail",
            18: "Insider Trading & Share Activity",
            19: "Aerospace & Aviation",
            20: "E-commerce & Amazon",
            21: "Social Media & Advertising",
            22: "Dividends & Energy Stocks",
            23: "Industrial Tech & Conglomerates",
            24: "ETFs & Asset Management",
            25: "AI & Semiconductors"
        }

        try:
            self.nmf_model = Nmf.load(self.nmf_model_path)
            self.dictionary = Dictionary.load(self.dict_path)
            self.tfidf_model = TfidfModel.load(self.tfidf_model_path)
            print("Topic modeling components loaded successfully.")
        except Exception as e:
            print(f"Failed to load topic modeling components: {e}")
            raise
        
    def extract_topics(self, text):
        """Extract topics from the given text.
        
        Args:
            text (str): The text to analyze
            
        Returns:
            list: List of dictionaries containing topic information
                  [{"name": "topic_name", "score": confidence_score}, ...]
        """
        try:
            # TODO: Your team will implement the topic extraction logic here
            print("Preprocessing news article...")
            tokens = self._preprocess_text(text)
            bow = self.dictionary.doc2bow(tokens)
            print("Extracting topics...")
            tfidf = self.tfidf_model[bow]
            topics = self.nmf_model[tfidf]

            sorted_topics = sorted(topics, key=lambda x: x[1], reverse=True)

            top_topics = []
            for idx, score in sorted_topics[:3]:
                topic_name = self.topic_labels.get(idx + 1, f"Topic {idx + 1}")
                top_topics.append({
                    "topic": topic_name,
                    "score": round(score, 4)
                })
            return top_topics
            
        except Exception as e:
            print(f"Error during topic modeling: {str(e)}")
            raise 

    def _preprocess_text(self, text):
        us_placeholder = "__US_PLACEHOLDER__"

        text = re.sub(r'<.*?>', '', text)
        text = html.unescape(html.unescape(text))
        text = re.sub(r'http\S+|www\.\S+', '', text)
        text = re.sub(r'U\.S\.', us_placeholder, text, flags=re.IGNORECASE)
        text = re.sub(r'\bUS\b', us_placeholder, text)

        try:
            text = contractions.fix(text)
        except Exception:
            pass

        text = re.sub(r"\b(\w+)'s\b", r"\1", text)
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        text = text.replace(us_placeholder, "U.S.")

        tokens = word_tokenize(text)
        tagged = pos_tag(tokens)

        def get_wordnet_pos(tag):
            if tag.startswith('J'): return wordnet.ADJ
            elif tag.startswith('V'): return wordnet.VERB
            elif tag.startswith('N'): return wordnet.NOUN
            elif tag.startswith('R'): return wordnet.ADV
            return wordnet.NOUN

        def resolve_us_token(token, pos):
            if pos == "NNP" and token.lower() == "us":
                return "united_states"
            return token

        lemmatized = [
            self.lemmatizer.lemmatize(resolve_us_token(token, pos), get_wordnet_pos(pos)).lower()
            for token, pos in tagged
        ]

        punctuation_artifacts = {"''", "'s", "``", "--", "-", "\\-", "...", "`", "p."}
        cleaned_tokens = [
            token for token in lemmatized
            if len(token) > 1 and token not in self.stopwords_set and token not in punctuation_artifacts and token.isalpha()
        ]

        return cleaned_tokens