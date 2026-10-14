import re
from collections import Counter
import torch
from transformers import pipeline
from config import SENTIMENT_MODEL, TOPIC_MODEL, TOPICS, MAX_TEXT_CHARS

STOPWORDS = set("""a an the and or but if then than to of in on at by for from with about as is are was were be been being it this that these those i you he she we they them my your our their me us do does did have has had not no yes very so too can could will would should may might just into over under again more most some any all what which who when where why how its""".split())

def clean_text(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()

def extract_keywords(text, limit=8):
    words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text.lower())
    counts = Counter(w for w in words if w not in STOPWORDS)
    return [w for w, _ in counts.most_common(limit)]

@__import__("streamlit").cache_resource(show_spinner="Loading pretrained AI models. First run may take several minutes…")
def load_pipelines():
    device = 0 if torch.cuda.is_available() else -1
    sentiment = pipeline("sentiment-analysis", model=SENTIMENT_MODEL, device=device)
    topic = pipeline("zero-shot-classification", model=TOPIC_MODEL, device=device)
    return sentiment, topic

def analyze_text(text, sentiment_pipe=None, topic_pipe=None):
    cleaned = clean_text(text)
    if not cleaned:
        raise ValueError("Please enter some text first.")
    if len(cleaned) > MAX_TEXT_CHARS:
        cleaned = cleaned[:MAX_TEXT_CHARS]
    if sentiment_pipe is None or topic_pipe is None:
        sentiment_pipe, topic_pipe = load_pipelines()
    sentiment_raw = sentiment_pipe(cleaned, truncation=True, max_length=512)[0]
    topic_raw = topic_pipe(cleaned, candidate_labels=TOPICS, multi_label=False)
    raw_label = str(sentiment_raw["label"]).lower()
    # CardiffNLP's model labels are normally negative/neutral/positive; normalize variants.
    if "pos" in raw_label or raw_label == "label_2":
        sentiment = "positive"
    elif "neg" in raw_label or raw_label == "label_0":
        sentiment = "negative"
    elif "neu" in raw_label or raw_label == "label_1":
        sentiment = "neutral"
    else:
        sentiment = raw_label
    return {
        "text": cleaned,
        "sentiment": sentiment,
        "sentiment_score": float(sentiment_raw["score"]),
        "topic": topic_raw["labels"][0],
        "topic_score": float(topic_raw["scores"][0]),
        "topic_labels": list(topic_raw["labels"]),
        "topic_scores": [float(x) for x in topic_raw["scores"]],
        "keywords": extract_keywords(cleaned),
        "word_count": len(cleaned.split()),
        "character_count": len(cleaned),
        "sentence_count": max(1, len(re.findall(r"[.!?]+", cleaned))) if cleaned else 0,
    }
