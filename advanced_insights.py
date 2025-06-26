import os
import json
from typing import List, Dict, Tuple

import pandas as pd
import plotly.express as px

from transformers import pipeline
from keybert import KeyBERT

def get_processed_path(app_id: int):
    return os.path.join("data", "processed", str(app_id), f"cleaned_{app_id}.json")


def get_output_dir(app_id: int):
    return os.path.join("data", "advanced_nlp", str(app_id))


def load_reviews(app_id: int) -> pd.DataFrame:
    path = get_processed_path(app_id)
    if not os.path.exists(path):
        raise FileNotFoundError("Cleaned reviews not found for this app. Run /process first.")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return pd.DataFrame(data.get("entries", []))


def transformer_sentiment(texts: List[str]) -> List[Dict]:
    """Run HF sentiment pipeline with safe truncation to 512 tokens.

    Some very long reviews (>512 tokens) caused shape mismatches inside the
    model. Passing an explicit ``max_length`` together with ``truncation=True``
    ensures the tokenizer will strictly cut sequences down to the supported
    length. ``padding=True`` keeps batch tensors aligned.
    """
    sent_pipe = pipeline(
        "sentiment-analysis",
        model="cardiffnlp/twitter-roberta-base-sentiment-latest",
        device=-1,  # CPU so that it works on most deployments
    )

    # Run in chunks to avoid OOM and ensure consistent tensor shapes
    batch_size = 32
    all_results: List[Dict] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        res = sent_pipe(batch, truncation=True, padding=True, max_length=512)
        all_results.extend(res)
    return all_results


def apply_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    texts = df["cleaned_content"].fillna("").astype(str).tolist()
    results = transformer_sentiment(texts)
    labels = []
    scores = []
    for r in results:
        label = r["label"].lower()
        if label == "neutral":
            sent = "neutral"
        elif label == "positive":
            sent = "positive"
        else:
            sent = "negative"
        labels.append(sent)
        scores.append(r["score"] if isinstance(r["score"], float) else 0.0)
    df["sentiment"] = labels
    df["sentiment_score"] = scores
    return df


def sentiment_metrics(df: pd.DataFrame) -> Dict:
    total = len(df)
    counts = df["sentiment"].value_counts().to_dict()
    percentages = {k: round(100 * v / total, 2) for k, v in counts.items()}
    avg_score = df["sentiment_score"].mean()
    return {
        "total_reviews": total,
        "counts": counts,
        "percentages": percentages,
        "average_score": avg_score,
    }


def keyword_extraction(df: pd.DataFrame, top_n: int = 50) -> Dict[str, List[Tuple[str, float]]]:
    kw_model = KeyBERT("all-MiniLM-L6-v2")
    keywords_by_sentiment: Dict[str, List[Tuple[str, float]]] = {}
    for sentiment in ["positive", "negative", "neutral"]:
        texts = df.loc[df["sentiment"] == sentiment, "cleaned_content"].tolist()
        if not texts:
            keywords_by_sentiment[sentiment] = []
            continue
        joined_text = " ".join(texts)
        keywords = kw_model.extract_keywords(joined_text, keyphrase_ngram_range=(1, 2), stop_words="english", top_n=top_n)
        keywords_by_sentiment[sentiment] = keywords
    return keywords_by_sentiment


def build_sunburst(df: pd.DataFrame, metrics: Dict, keywords: Dict[str, List[Tuple[str, float]]], app_id: int):
    labels = ["Reviews"]
    parents = [""]
    values = [metrics["total_reviews"]]

    for sentiment in ["positive", "negative", "neutral"]:
        count = metrics["counts"].get(sentiment, 0)
        if count == 0:
            continue
        labels.append(sentiment.capitalize())
        parents.append("Reviews")
        values.append(count)

        for word, score in keywords.get(sentiment, [])[:50]:
            labels.append(word)
            parents.append(sentiment.capitalize())
            # Use score as value proxy; alternatively use frequency
            values.append(round(score * 100, 2))

    fig = px.sunburst(
        names=labels,
        parents=parents,
        values=values,
        title="Advanced Sentiment & Keyword Sunburst",
    )
    fig.update_traces(insidetextorientation="radial")

    out_dir = get_output_dir(app_id)
    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(out_dir, "advanced_sentiment_sunburst.html")
    fig.write_html(html_path)
    print(f"Sunburst saved to {html_path}")


def generate_insights(keywords: Dict[str, List[Tuple[str, float]]]) -> List[str]:
    insights = []
    # Focus on negative keywords for improvement ideas
    neg_keywords = [kw for kw, score in keywords.get("negative", [])[:50]]
    if any(k in neg_keywords for k in ["price", "subscription", "pay"]):
        insights.append("Pricing concerns detected. Consider revisiting subscription plans or offering trials.")
    if any(k in neg_keywords for k in ["bug", "crash", "error", "issue"]):
        insights.append("Users report stability issues. Prioritize bug fixes and QA.")
    if any(k in neg_keywords for k in ["login", "account", "sign"]):
        insights.append("Login or account issues prevalent. Simplify authentication flow.")
    if any(k in neg_keywords for k in ["ads", "advert"]):
        insights.append("Negative sentiment around ads. Evaluate frequency and placement of advertisements.")
    if any(k in neg_keywords for k in ["slow", "lag", "performance"]):
        insights.append("Performance issues noted. Optimize app speed and responsiveness.")
    # New rule: complaints comparing the app to YouTube or other streaming services
    if any(k in neg_keywords for k in ["youtube", "streaming", "video", "channel"]):
        insights.append(
            "Users compare the app with YouTube/other streaming platforms and question the subscription's value. Clearly communicate unique offerings, consider content diversification, and evaluate pricing tiers."
        )
    if not insights:
        insights.append("Sentiment analysis did not highlight specific dominant issues. Continue monitoring.")
    return insights


def save_results(metrics: Dict, keywords: Dict[str, List[Tuple[str, float]]], insights: List[str], app_id: int):
    output = {
        "sentiment_metrics": metrics,
        # Store ONLY negative keywords for concise JSON output
        "negative_keywords": [{"keyword": kw, "score": float(sc)} for kw, sc in keywords.get("negative", [])],
        "insights": insights,
    }
    out_dir = get_output_dir(app_id)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "advanced_nlp_insights.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"Advanced NLP insights saved to {path}")


def main(app_id: int):
    df = load_reviews(app_id)
    df = apply_sentiment(df)
    metrics = sentiment_metrics(df)
    keywords = keyword_extraction(df, top_n=50)

    print("=== Advanced Sentiment Metrics ===")
    for k, v in metrics["percentages"].items():
        print(f"{k.capitalize()}: {v}% ({metrics['counts'][k]} reviews)")

    print("\nTop Negative Keywords:")
    for kw, score in keywords["negative"][:20]:
        print(f"  {kw}: {round(score, 3)}")

    insights = generate_insights(keywords)
    print("\nActionable Insights:")
    for i, ins in enumerate(insights, 1):
        print(f"{i}. {ins}")

    build_sunburst(df, metrics, keywords, app_id)
    save_results(metrics, keywords, insights, app_id)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("app_id", type=int)
    args = parser.parse_args()
    main(args.app_id) 