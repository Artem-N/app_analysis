# App Analysis

Project for analyzing applications from the App Store.

## Description
This project is designed to analyze various aspects of applications from the Apple App Store, including reviews, ratings, and metadata.

## Features

### Core Functionality
- **App Search**: Search for apps by name
- **Review Analysis**: Collect and analyze app reviews with statistics
- **Data Export**: Save analysis results to JSON files 
- **Multi-country Support**: Analyze apps in different regional App Stores

### Error Handling
The project includes error handling for:
- **Input Validation**: Validates app IDs, country codes, and search terms
- **Network Errors**: Handles timeouts, connection errors, and HTTP errors
- **Data Processing**: Safely processes missing or invalid review data
- **File Operations**: Handles permission errors and creates backups
- **API Errors**: Manages App Store API limitations and errors

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Artem-N/app_analysis.git
cd app_analysis
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```


## Running the REST API locally

The following steps walk you through running the FastAPI service locally.

1. Create and activate a virtual environment (optional):
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Start the server with live-reload enabled:
```bash
uvicorn api_main:app --reload --port 8000
```
4. Open **http://127.0.0.1:8000/** in the browser — a minimal web UI (`static/index.html`) will appear.
5. (Alternative) Explore the automatic Swagger docs at **http://127.0.0.1:8000/docs**.

## Architecture & Design Choices

1. **Modularity** – each stage (collect → cleaning → core metrics → advanced NLP) lives in its own module and REST endpoint, which simplifies debugging and scaling.
2. **Proper REST semantics** –  
   • POST to /collect, /process, /visualization, /sunburst creates or updates resources;  
   • GET to /visualization, /sunburst, /metrics_summary only retrieves already generated data;  
   • thus GET remains safe/idempotent while POST performs state-changing work.
3. **Lazy generation & caching** – heavy computations (plots, NLP) run only once and are cached under `data/…`; subsequent GET requests just serve the static HTML/JSON.
4. **Pure-static front-end** – the UI is plain HTML + Fetch API, so the service can be deployed on any ASGI server without template engines.
5. **Predictable file layout** – all output artifacts are stored under `data/` with a clear hierarchy, making them easy to back-up or inspect offline.
6. **Multi-country support** – the `countries` parameter accepts multiple 2-letter codes; cleaning adds a `country` field to every review record.
7. **Resource-friendly** – large models (`transformers`, `keybert`) run in CPU mode, enabling the service to work even on low-spec VPSs.

## Sample NLP Insight Report

Below is a trimmed example of the JSON report (`data/advanced_nlp/1447033725/advanced_nlp_insights.json`) produced after running the full pipeline for **Nebula – Streaming Platform** (app ID 1447033725, country US, 500 reviews).

```json
{
  "sentiment_metrics": {
    "total_reviews": 100,
    "counts": {
      "positive": 50,
      "negative": 34,
      "neutral": 16
    },
    "percentages": {
      "positive": 50,
      "negative": 34,
      "neutral": 16
    },
    "average_score": 0.7683645895123482
  },
  "negative_keywords": [
    {"keyword": "subscription", "score": 0.54},
    {"keyword": "youtube", "score": 0.51},
    {"keyword": "price", "score": 0.50},
  ],
  "insights": [
    "Pricing concerns detected. Consider revisiting subscription plans or offering trials.",
    "Users compare the app with YouTube/other streaming platforms and question the subscription's value."
  ]
}
```

*Interpretation*: more than 38 % of reviews are negative and most frequently mention **subscription**, **price**, and **YouTube** – this suggests dissatisfaction with pricing and competition from free platforms.

## REST API Endpoints

After the server is running on `http://127.0.0.1:8000`, you can exercise every stage through the following requests (all examples use the demo app id **1447033725**).

| # | Verb | Endpoint | Purpose | Example |
|---|------|----------|---------|---------|
|1|GET|/search|Search apps by name & country|`/search?name=Nebula&country=us`|
|2|POST|/collect|Fetch raw reviews for one or more countries|`/collect?app_id=1447033725&countries=us&countries=gb&limit=100`|
|3|POST|/process|Clean the previously collected reviews|`/process?app_id=1447033725`|
|4|GET|/processed/{id}|Download cleaned JSON|`/processed/1447033725`|
|5|POST|/visualization/{id}|Generate bar-chart HTML + metrics|`/visualization/1447033725`|
|6|GET|/visualization/{id}|Open the bar-chart|`/visualization/1447033725`|
|7|GET|/visualization/{id}?download=true|Download the bar-chart HTML|`/visualization/1447033725?download=true`|
|8|GET|/metrics_summary/{id}|Retrieve metrics JSON|`/metrics_summary/1447033725`|
|9|POST|/sunburst/{id}|Generate sunburst HTML + NLP insights|`/sunburst/1447033725`|
|10|GET|/sunburst/{id}|Open the sunburst graph|`/sunburst/1447033725`|
|11|GET|/sunburst/{id}?download=true|Download the sunburst HTML|`/sunburst/1447033725?download=true`|
|12|GET|/insights/{id}|Download NLP insight JSON|`/insights/1447033725`|
|13|GET|/reviews/{country}|Download raw review JSON|`/reviews/us`|
|14|GET|/metrics|Legacy global metrics (if generated)|`/metrics`|



Tip: POST calls can be executed from a browser console:
```js
fetch('http://127.0.0.1:8000/process?app_id=1447033725', {method: 'POST'})
```
Or through cURL:
```bash
curl -X POST "http://127.0.0.1:8000/visualization/1447033725"
```