import json
import glob
import os
import re
from typing import List, Dict
from datetime import datetime

RAW_DIR_BASE = os.path.join("data", "raw")
PROCESSED_BASE = os.path.join("data", "processed")

# Regular expression patterns
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
# Punctuation & symbol removal: replace any character that is NOT a word character or whitespace
# Using Unicode-aware pattern without \p{{...}} (unsupported in std re module)
NON_WORD_PATTERN = re.compile(r"[^\w\s]", re.UNICODE)

# Basic list of English stopwords (can be expanded). Short function words will be removed.
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to", "for", "of",
    "is", "it", "be", "as", "by", "this", "that", "with", "from", "are", "was", "were", "so",
    "we", "he", "she", "they", "you", "i", "me", "my", "our", "your", "their"
}


def clean_text(text: str) -> str:
    """Clean and preprocess review text.

    Steps:
    1. Lowercase text
    2. Remove URLs
    3. Remove punctuation and symbols
    4. Remove extra whitespace
    5. Remove stopwords
    """
    if not text:
        return ""

    # Lowercase
    text = text.lower()

    # Remove URLs
    text = URL_PATTERN.sub(" ", text)

    # Remove punctuation and symbols (non-word, non-space chars)
    text = NON_WORD_PATTERN.sub(" ", text)

    # Remove extra whitespace
    text = re.sub("\s+", " ", text).strip()

    # Remove stopwords
    tokens = [tok for tok in text.split() if tok not in STOPWORDS]
    text = " ".join(tokens)

    return text


def load_reviews(file_path: str) -> List[Dict]:
    """Load reviews from a JSON analysis file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("reviews", [])
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error loading {file_path}: {e}")
        return []


def process_reviews(app_id: int) -> List[Dict]:
    """Process raw review files for a specific app_id and return cleaned entries."""
    pattern = os.path.join(RAW_DIR_BASE, "*", f"app_{app_id}_reviews_*.json")
    files = glob.glob(pattern)
    if not files:
        print("No raw review files found for this app.")
        return []

    cleaned_entries: List[Dict] = []

    for file_path in files:
        country = os.path.basename(os.path.dirname(file_path))

        reviews = load_reviews(file_path)
        for review in reviews:
            try:
                cleaned_entry = {
                    "id": review.get("id"),
                    "country": country,
                    "rating": review.get("rating"),
                    "title": review.get("title", ""),
                    "content": review.get("content", ""),
                    "cleaned_title": clean_text(review.get("title", "")),
                    "cleaned_content": clean_text(review.get("content", "")),
                }
                cleaned_entries.append(cleaned_entry)
            except Exception as e:
                print(f"Error processing review {review.get('id')}: {e}")
                continue

    return cleaned_entries


def save_cleaned_reviews(entries: List[Dict], app_id: int) -> str:
    """Save cleaned entries to processed directory per app and return path."""
    out_dir = os.path.join(PROCESSED_BASE, str(app_id))
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"cleaned_{app_id}.json")

    try:
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({
                "processed_at": datetime.now().isoformat(),
                "total_entries": len(entries),
                "entries": entries,
            }, f, ensure_ascii=False, indent=2)
        print(f"Cleaned reviews saved to {out_file} ({len(entries)} entries)")
        return out_file
    except OSError as e:
        print(f"Error saving cleaned reviews: {e}")
        return ""


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("app_id", type=int)
    args = parser.parse_args()

    entries = process_reviews(args.app_id)
    if entries:
        save_cleaned_reviews(entries, args.app_id) 