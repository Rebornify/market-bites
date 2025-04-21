import os
import re
import html
import contractions
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class SentimentAnalyzer:
    def __init__(self, model_path=None):
        """Initialize the sentiment analyzer with FinBERT model and tokenizer."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_dir = model_path or os.path.join(base_dir, 'models', 'finbert_sentiment')

        print(f"Loading FinBERT from: {model_dir}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()

    def preprocess(self, text):
        def remove_markdown(t):
            t = re.sub(r'\*\*(.*?)\*\*', r'\1', t)
            t = re.sub(r'__(.*?)__', r'\1', t)
            t = re.sub(r'\*(.*?)\*', r'\1', t)
            t = re.sub(r'_(.*?)_', r'\1', t)
            t = re.sub(r'^\s*#+\s*(.*?)\s*#*\s*$', r'\1', t, flags=re.MULTILINE)
            t = re.sub(r'^\s*>\s?(.*)', r'\1', t, flags=re.MULTILINE)
            t = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', t)
            t = re.sub(r'`{1,3}(.*?)`{1,3}', r'\1', t, flags=re.DOTALL)
            t = re.sub(r'~~(.*?)~~', r'\1', t)
            t = re.sub(r'^\s*[\*\-\+]\s+', '', t, flags=re.MULTILINE)
            t = re.sub(r'^\s*\d+\.\s+', '', t, flags=re.MULTILINE)
            t = re.sub(r'^\s*[-*_]{3,}\s*$', '', t, flags=re.MULTILINE)
            return t

        text = re.sub(r'<.*?>', '', text)
        text = html.unescape(html.unescape(text))
        text = re.sub(r'\b[/\\]?[ur]/\w+\b', '', text)
        text = remove_markdown(text)
        text = re.sub(r'^\s*[|: -]+\|?\s*$\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'^.*\|(?:.*\|)+.*$\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'http\S+|www\.\S+', '', text)
        try:
            text = contractions.fix(text)
        except:
            pass
        text = re.sub(r'\\n+|\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def analyze(self, text):
        """Analyze the sentiment of the given text.
        
        Args:
            text (str): The text to analyze.
        
        Returns:
            dict: Sentiment results.
        """
        try:
            cleaned_text = self.preprocess(text)
            inputs = self.tokenizer(
                cleaned_text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=256
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.nn.functional.softmax(logits, dim=1)
                predicted_class = torch.argmax(probs, dim=1).item()
                confidence = probs[0, predicted_class].item()

            sentiment_map = {
                1: "Very negative",
                2: "Negative",
                3: "Neutral",
                4: "Positive",
                5: "Very positive"
            }

            score = predicted_class + 1

            return {
                "sentiment": sentiment_map.get(score, "Unknown"),
                "score": score,
                "confidence": round(confidence, 4),
                "class_probabilities": probs[0].tolist()
            }

        except Exception as e:
            print(f"Error during sentiment analysis: {str(e)}")
            raise
