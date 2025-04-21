from transformers import BartTokenizer, BartForConditionalGeneration
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.tokenize import sent_tokenize
import numpy as np
import torch
import re
import textstat
import contractions
import html 
import emoji

def remove_emojis(text):
    return emoji.replace_emoji(text, replace='')


# Might have python version error where some emojis aren't recognised, so use the above 
# def remove_emojis(text):
#     emoji_pattern = re.compile(
#         "["
#         u"\U0001F600-\U0001F64F"  # Emoticons
#         u"\U0001F300-\U0001F5FF"  # Symbols & pictographs
#         u"\U0001F680-\U0001F6FF"  # Transport & map symbols
#         u"\U0001F1E0-\U0001F1FF"  # Flags
#         u"\U00002700-\U000027BF"  # Dingbats
#         u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
#         u"\U00002600-\U000026FF"  # Misc symbols
#         u"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
#         "]+",
#         flags=re.UNICODE
#     )
#     return emoji_pattern.sub(r'', text)

def remove_common_bart_artifacts(text):
    patterns = [
        r"(?i)visit cnn\.com.*", 
        r"(?i)click here to.*", 
        r"(?i)iReporter.*Travel Snapshots.*",
        r"(?i)cnn\.com will feature.*travel snapshots.*",  
        r"(?i)cnn\.com will feature.*",                    
        r"(?i)for a new gallery.*",                       
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text).strip()
    return text

def remove_markdown(text):
    """Removes common markdown formatting."""
    # Replace literal '\n' strings and actual newlines with a space
    text = re.sub(r'\\n+|\n+', ' ', text)
    # Bold: **text** or __text__
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    # Italics: *text* or _text_
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text) # Note: This might conflict with underscores in words if not handled carefully later
    # Headers: Remove leading # and trailing #
    text = re.sub(r'^\s*#+\s*(.*?)\s*#*\s*$', r'\1', text, flags=re.MULTILINE)
    # Blockquotes: Remove leading >
    text = re.sub(r'^\s*>\s?(.*)', r'\1', text, flags=re.MULTILINE)
    # Links: [text](url) -> text
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    # Code blocks (inline and block) - remove backticks and fences
    text = re.sub(r'`{1,3}(.*?)`{1,3}', r'\1', text, flags=re.DOTALL)
    # Strikethrough: ~~text~~
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    # List items (remove bullets/numbers at the start of lines)
    text = re.sub(r'^\s*[\*\-\+]\s+', '', text, flags=re.MULTILINE) # Unordered list markers
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE) # Ordered list markers
    # Horizontal rules
    text = re.sub(r'^\s*[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)

    return text.strip() # Return stripped text to remove leading/trailing whitespace

def safe_expand_contractions(text):
    words = text.split()
    expanded_words = []
    for word in words:
        if word.isupper() and len(word) <= 4:  # protect acronyms like US, UK, GDP
            expanded_words.append(word)
        else:
            expanded_words.append(contractions.fix(word))
    return ' '.join(expanded_words)


def initial_clean(text):
    """Performs initial text cleaning common to most pipelines."""
    # --- Original Cleaning Steps FIRST ---
    text = remove_emojis(text)
    text = re.sub(r'<.*?>', '', text)                       # Remove HTML tags
    text = html.unescape(text)                              # Unescape HTML entities
    text = html.unescape(text)
    text = re.sub(r'\b[/\\]?[ur]/\w+\b', '', text)           # Remove r/u/ references
    text = remove_markdown(text)                          # Apply general markdown formatting removal
    text = re.sub(r'^\s*[|: -]+\|?\s*$\n?', '', text, flags=re.MULTILINE) # Table separators
    text = re.sub(r'^.*\|(?:.*\|)+.*$\n?', '', text, flags=re.MULTILINE) # Table content
    text = re.sub(r'http\S+|www\.\S+', '', text)             # Remove URLs
    # --- Final Cleanup ---
    text = re.sub(r'\\n+|\n+', ' ', text)                   # Replace newlines with space
    text = re.sub(r'\s+', ' ', text).strip()           # Normalize whitespace
    text = safe_expand_contractions(text)
    return text

class TextSummarizer:
    def __init__(self):
        """Initialize the text summarization component. """ 
        self.tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
        self.model =  BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")

        # If model keeps crashing, use these
        # self.tokenizer = BartTokenizer.from_pretrained("sshleifer/distilbart-cnn-12-6")
        # self.model = BartForConditionalGeneration.from_pretrained("sshleifer/distilbart-cnn-12-6")

    
    def readability_adjusted_top_k(self, text, min_k=3, max_k=6):
        sentences = sent_tokenize(text)
        sentence_count = len(sentences)
        readability_score = textstat.flesch_reading_ease(text)

        # More complex = more sentences included
        if readability_score >= 60:
            ratio = 0.2  # easy to read, fewer sentences
        elif 30 <= readability_score < 60:
            ratio = 0.3
        else:
            ratio = 0.4  # hard to read, keep more sentences

        top_k = int(sentence_count * ratio)
        return max(min_k, min(top_k, max_k, sentence_count))

    def extract_top_sentences(self, text, top_k=4):
        sentences = sent_tokenize(text)
        if len(sentences) <= top_k:
            return ' '.join(sentences)
        
        vectorizer = TfidfVectorizer().fit_transform(sentences)
        similarity_matrix = cosine_similarity(vectorizer)

        # Rank by sum of similarities (basic centrality)
        scores = similarity_matrix.sum(axis=1)
        ranked_indices = np.argsort(scores)[::-1]
        top_sentences = [sentences[i] for i in ranked_indices[:top_k]]
        return ' '.join(top_sentences)
        
    def summarize(self, text, max_length=100):
        """Generate a summary of the given text.
        
        Args:
            text (str): The text to summarize
            max_length (int, optional): Maximum length of the summary in words
            
        Returns:
            dict: Contains the generated summary and metadata
                  {"summary": "...", "confidence": 0.95}
        """
        try:
            # Extract top informative sentences first
            print("Processing for summary...")
            processed = initial_clean(text)

            top_k = self.readability_adjusted_top_k(processed)

            filtered = self.extract_top_sentences(processed, top_k=top_k)
          
            # Tokenize and generate summary
            print("Generating summary...")
            inputs = self.tokenizer(
                filtered,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )

            with torch.no_grad():
                summary_ids = self.model.generate(
                    inputs.input_ids,
                    num_beams=5,
                    max_length=max_length,
                    min_length=30,
                    early_stopping=True,
                    length_penalty=1.0,
                    no_repeat_ngram_size=2
                )

            decoded = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)

            # to cut the summary off at the last complete sentence
            clean_summary = decoded[:decoded.rfind('.') + 1] if '.' in decoded else decoded
            cleaned_summary = remove_common_bart_artifacts(clean_summary)

            # Fallback: use first sentence of original input if summary is empty
            if not cleaned_summary.strip():
                print("Summary was empty after artifact removal. Falling back to first sentence.")
                fallback_summary = sent_tokenize(text)[0] if sent_tokenize(text) else ''
                return fallback_summary

            return cleaned_summary
            
        except Exception as e:
            print(f"Error during text summarization: {str(e)}")
            raise 