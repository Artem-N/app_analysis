import json
import os
from typing import Dict, List

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Input file with cleaned reviews
def get_processed_path(app_id: int):
    return os.path.join("data", "processed", str(app_id), f"cleaned_{app_id}.json")

# Output directory for metrics and visualizations
def get_output_dir(app_id: int):
    return os.path.join("data", "metrics", str(app_id))

RATING_RANGE = [1, 2, 3, 4, 5]


def load_cleaned_reviews(path: str) -> List[Dict]:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Processed reviews file not found: {path}. Run data_processing.py first."
        )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("entries", [])


def calculate_metrics(reviews: List[Dict]):
    if not reviews:
        return {
            "average_rating": 0,
            "rating_counts": {r: 0 for r in RATING_RANGE},
            "total_reviews": 0,
        }

    valid_reviews = [r for r in reviews if isinstance(r.get("rating"), (int, float))]
    total_reviews = len(valid_reviews)

    rating_counts = {r: 0 for r in RATING_RANGE}
    rating_sum = 0

    for rev in valid_reviews:
        rating = int(rev["rating"])
        if rating in rating_counts:
            rating_counts[rating] += 1
        rating_sum += rating

    avg_rating = rating_sum / total_reviews if total_reviews > 0 else 0

    return {
        "average_rating": avg_rating,
        "rating_counts": rating_counts,
        "total_reviews": total_reviews,
    }


def visualize_distribution(metrics: Dict, output_dir: str):
    rating_counts = metrics["rating_counts"]
    total = metrics["total_reviews"]

    ratings = list(rating_counts.keys())
    counts = [rating_counts[r] for r in ratings]
    percentages = [round(100 * c / total, 2) if total else 0 for c in counts]

    fig = px.bar(
        x=[str(r) + "-star" for r in ratings],
        y=counts,
        text=[f"{p}%" for p in percentages],
        labels={"x": "Rating", "y": "Number of Reviews"},
        title=f"Ratings Distribution (Average: {metrics['average_rating']:.2f} | Total: {total})",
    )

    fig.update_traces(textposition="outside")
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode="hide")

    # Show the figure in a browser window
    fig.show()

    # Save to HTML for future reference
    os.makedirs(output_dir, exist_ok=True)
    output_html = os.path.join(output_dir, "ratings_distribution.html")
    fig.write_html(output_html)
    print(f"Interactive chart saved to {output_html}")


def main(app_id: int):
    try:
        processed_path = get_processed_path(app_id)
        reviews = load_cleaned_reviews(processed_path)
    except FileNotFoundError as e:
        print(e)
        return

    metrics = calculate_metrics(reviews)

    print("=== Metrics ===")
    print(f"Total reviews: {metrics['total_reviews']}")
    print(f"Average rating: {metrics['average_rating']:.2f}")
    print("Rating counts:")
    for r in sorted(metrics["rating_counts"].keys(), reverse=True):
        count = metrics["rating_counts"][r]
        perc = 100 * count / metrics["total_reviews"] if metrics["total_reviews"] else 0
        print(f"  {r}-star: {count} ({perc:.2f}%)")

    output_dir = get_output_dir(app_id)
    visualize_distribution(metrics, output_dir)

    # Save metrics to files
    save_metrics(metrics, output_dir)


def save_metrics(metrics: Dict, output_dir: str):
    """Save metrics to JSON and CSV files inside data/processed."""
    os.makedirs(output_dir, exist_ok=True)

    # JSON summary
    json_path = os.path.join(output_dir, "metrics_summary.json")
    with open(json_path, "w", encoding="utf-8") as f_json:
        json.dump(metrics, f_json, indent=2)
    print(f"Metrics JSON saved to {json_path}")

    # CSV summary
    csv_path = os.path.join(output_dir, "rating_distribution.csv")
    with open(csv_path, "w", encoding="utf-8") as f_csv:
        f_csv.write("Rating,Count,Percentage\n")
        for r in sorted(metrics["rating_counts"].keys(), reverse=True):
            count = metrics["rating_counts"][r]
            perc = 100 * count / metrics["total_reviews"] if metrics["total_reviews"] else 0
            f_csv.write(f"{r},{count},{perc:.2f}\n")
    print(f"Metrics CSV saved to {csv_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("app_id", type=int)
    args = parser.parse_args()
    main(args.app_id) 