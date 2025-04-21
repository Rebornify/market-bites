import spacy
import re
import html
import contractions
import os

def safe_expand_contractions(text):
    words = text.split()
    expanded_words = []
    for word in words:
        if word.isupper() and len(word) <= 4:  # protect acronyms like US, UK, GDP
            expanded_words.append(word)
        else:
            expanded_words.append(contractions.fix(word))
    return ' '.join(expanded_words)

def remove_markdown(text):
    """Removes common markdown formatting."""
    text = re.sub(r'\\n+|\n+', ' ', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'^\s*#+\s*(.*?)\s*#*\s*$', r'\1', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*>\s?(.*)', r'\1', text, flags=re.MULTILINE)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'`{1,3}(.*?)`{1,3}', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    text = re.sub(r'^\s*[\*\-\+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    return text.strip()

def initial_clean(text):
    """Performs initial text cleaning common to most pipelines."""
    text = re.sub(r'<.*?>', '', text)                       # Remove HTML tags
    text = html.unescape(text)                              # Unescape HTML entities
    text = html.unescape(text)
    text = re.sub(r'\b[/\\]?[ur]/\w+\b', '', text)           # Remove r/u/ references
    text = remove_markdown(text)                            # Apply general markdown formatting removal
    text = re.sub(r'^\s*[|: -]+\|?\s*$\n?', '', text, flags=re.MULTILINE) # Table separators
    text = re.sub(r'^.*\|(?:.*\|)+.*$\n?', '', text, flags=re.MULTILINE) # Table content
    text = re.sub(r'http\S+|www\.\S+', '', text)             # Remove URLs
    text = safe_expand_contractions(text)                        # Expand contractions *after* URL/tag removal
    # --- Final Cleanup ---
    text = re.sub(r'\\n+|\n+', ' ', text)                   # Replace newlines with space
    text = re.sub(r'\s+', ' ', text).strip()           # Normalize whitespace
    return text

class NERNewsModel:
    def __init__(self, model_name='ner_news'):
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_path, 'models', model_name)
        print(f"Loading spaCy NER model(news) from: {model_path}")
        self.nlp = spacy.load(model_path)

    def extract_entities(self, title, summary):
        """Cleans the text and extracts named entities."""
        combined_text = f"{title.strip()}. {summary.strip()}"
        cleaned = initial_clean(combined_text)
        doc = self.nlp(cleaned)
        return [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
