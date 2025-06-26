from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List
import os
import json
import plotly.express as px

from app_store_web_scraper import AppStoreEntry, AppNotFound
from datetime import datetime

# Our internal modules
import data_processing
import advanced_insights
from find_app_id import search_app_store
import extract_info

# External for quick HTML generation
import plotly.express as px

# Metrics module
import metrics_visualization

app = FastAPI(title="App Review Analysis API", version="1.0")

RAW_DIR_BASE = os.path.join("data", "raw")

# Serve static front-end
app.mount("/static", StaticFiles(directory="static", html=True), name="static")


def _collect_raw(app_id: int, countries: List[str], limit: int):
    """Only collect raw reviews and save to data/raw."""
    saved_files: List[str] = []
    for country in countries:
        try:
            entry = AppStoreEntry(app_id=app_id, country=country)
            reviews = []
            for rev in entry.reviews(limit=limit):
                reviews.append(
                    {
                        "id": rev.id,
                        "date": rev.date.isoformat(),
                        "user_name": rev.user_name,
                        "title": rev.title,
                        "content": rev.content,
                        "rating": rev.rating,
                        "app_version": rev.app_version,
                    }
                )

            dir_path = os.path.join(RAW_DIR_BASE, country)
            os.makedirs(dir_path, exist_ok=True)
            filepath = os.path.join(dir_path, f"app_{app_id}_reviews_{country}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "app_id": app_id,
                        "country": country,
                        "retrieved": datetime.now().isoformat(),
                        "reviews": reviews,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            saved_files.append(filepath)
        except AppNotFound:
            raise HTTPException(status_code=404, detail=f"App {app_id} not found in {country}")

    return saved_files


@app.post("/collect")
def collect_reviews(app_id: int = Query(..., description="App Store ID of the app"),
                   countries: List[str] = Query(["us"], description="Country codes"),
                   limit: int = Query(500, ge=1, le=5000, description="Max reviews per country")):
    """Collect raw reviews for given app ID and countries (no processing)."""
    try:
        files = _collect_raw(app_id, countries, limit)
        return {"status": "collected", "files": files}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
def get_metrics():
    """Return calculated metrics summary JSON."""
    path = os.path.join("data", "metrics", "metrics_summary.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Metrics not found. Run /collect first.")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return JSONResponse(content=data)


@app.get("/metrics_summary/{app_id}")
def get_metrics_summary(app_id: int):
    """Return metrics summary JSON for the given app ID."""
    path = os.path.join("data", "metrics", str(app_id), "metrics_summary.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Metrics summary not found. Run /process or /collect first.")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return JSONResponse(content=data)


@app.get("/insights/{app_id}")
def get_insights(app_id: int, download: bool = Query(False, description="Return as attachment")):
    path = os.path.join("data", "advanced_nlp", str(app_id), "advanced_nlp_insights.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Insights not found. Run /process or /collect first.")

    if download:
        filename = os.path.basename(path)
        headers = {"Content-Disposition": f"attachment; filename={filename}"}
        return FileResponse(path=path, media_type="application/json", headers=headers)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return JSONResponse(content=data)


@app.get("/reviews/{country}")
def download_reviews(country: str):
    dir_path = os.path.join(RAW_DIR_BASE, country)
    # find any json in dir (assuming one per app)
    if not os.path.isdir(dir_path):
        raise HTTPException(status_code=404, detail="No reviews for this country.")
    files = [f for f in os.listdir(dir_path) if f.endswith(".json")]
    if not files:
        raise HTTPException(status_code=404, detail="No review file found.")
    # send first file (or could param app_id)
    file_path = os.path.join(dir_path, files[0])
    return FileResponse(path=file_path, filename=os.path.basename(file_path), media_type="application/json")


@app.get("/search")
def search_app(name: str = Query(..., description="App name to search in App Store"),
               country: str = Query("us", min_length=2, max_length=2, description="2-letter country code")):
    """Search App Store for apps matching the given name and country. Returns list of candidates."""
    try:
        results = search_app_store(name, country)
        if not results:
            raise HTTPException(status_code=404, detail="No apps found for given query")
        return results
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------- EXTRACT INFO ENDPOINT -----------------


@app.post("/extract")
def extract_details(app_id: int = Query(..., description="App Store ID"),
                    countries: List[str] = Query(["us"], description="Country codes")):
    """Run detailed extraction for specified app_id and countries."""
    try:
        result = extract_info.analyze_app(app_id, countries)
        return {"status": "completed", "detail": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ----------------- PROCESSING & DOWNLOAD ENDPOINTS -----------------


@app.post("/process")
def process_reviews_endpoint(app_id: int = Query(..., description="App Store ID")):
    """Process raw review files into cleaned dataset and return cleaned JSON. Не рахуємо жодних метрик."""
    cleaned = data_processing.process_reviews(app_id)
    if not cleaned:
        raise HTTPException(status_code=404, detail="No raw review files found to process.")

    # Save cleaned data to disk
    saved_path = data_processing.save_cleaned_reviews(cleaned, app_id)

    # Повертаємо JSON вмісту очищених даних
    try:
        with open(saved_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read cleaned data: {e}")

    return JSONResponse(content=data)


@app.get("/processed/{app_id}")
def download_processed_app(app_id: int):
    """Download cleaned data for specified app_id."""
    path = os.path.join("data", "processed", str(app_id), f"cleaned_{app_id}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Processed file for this app_id not found. Run /process or /collect first.")
    return FileResponse(path=path, filename=f"cleaned_{app_id}.json", media_type="application/json")


# ----------------- VISUALIZATION ENDPOINT -----------------


def _generate_metrics_html(app_id: int) -> str:
    html_path = os.path.join(metrics_visualization.get_output_dir(app_id), "ratings_distribution.html")
    if os.path.exists(html_path):
        return html_path

    # generate
    processed_path = metrics_visualization.get_processed_path(app_id)
    if not os.path.exists(processed_path):
        raise HTTPException(status_code=404, detail="Processed data not found for this app id")

    reviews = metrics_visualization.load_cleaned_reviews(processed_path)
    metrics = metrics_visualization.calculate_metrics(reviews)

    ratings = list(metrics["rating_counts"].keys())
    counts = [metrics["rating_counts"][r] for r in ratings]
    percentages = [round(100 * c / metrics["total_reviews"], 2) if metrics["total_reviews"] else 0 for c in counts]

    fig = px.bar(
        x=[f"{r}-star" for r in ratings],
        y=counts,
        text=[f"{p}%" for p in percentages],
        labels={"x": "Rating", "y": "Number of Reviews"},
        title=f"Ratings Distribution (Avg {metrics['average_rating']:.2f})",
    )
    fig.update_traces(textposition="outside")

    out_dir = metrics_visualization.get_output_dir(app_id)
    os.makedirs(out_dir, exist_ok=True)
    fig.write_html(html_path)

    # Зберігаємо metrics_summary.json та CSV
    metrics_visualization.save_metrics(metrics, out_dir)
    return html_path


@app.get("/visualization/{app_id}")
def get_visualization(app_id: int, download: bool = Query(False, description="Якщо true – повернути файл як attachment")):
    """Return ratings distribution HTML for given app_id (генерує якщо відсутній).

    Параметр download дозволяє віддати файл як вкладення для завантаження.
    """
    try:
        html_path = os.path.join(metrics_visualization.get_output_dir(app_id), "ratings_distribution.html")
        if not os.path.exists(html_path):
            raise HTTPException(status_code=404, detail="Visualization not generated. Call POST /visualization/{app_id} first.")
        if download:
            filename = os.path.basename(html_path)
            headers = {"Content-Disposition": f"attachment; filename={filename}"}
            return FileResponse(path=html_path, media_type="text/html", headers=headers)
        # inline view – без headers та filename, щоб браузер відкрив у вкладці
        return FileResponse(path=html_path, media_type="text/html")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/visualization/{app_id}")
def generate_visualization(app_id: int):
    """Generate rating distribution HTML and metrics files, return HTML."""
    try:
        html_path = _generate_metrics_html(app_id)
        return FileResponse(path=html_path, media_type="text/html")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", response_class=HTMLResponse)
async def root_page():
    """Return front-end HTML page."""
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Front-end not found. Make sure static/index.html exists.</h1>"


# ----------------- SUNBURST ENDPOINT -----------------


def _generate_sunburst_html(app_id: int) -> str:
    html_path = os.path.join(
        advanced_insights.get_output_dir(app_id),
        "advanced_sentiment_sunburst.html",
    )
    if os.path.exists(html_path):
        return html_path

    # generate via advanced_insights (will also save insights json)
    advanced_insights.main(app_id)
    if not os.path.exists(html_path):
        raise HTTPException(status_code=500, detail="Failed to generate sunburst chart.")
    return html_path


@app.get("/sunburst/{app_id}")
def get_sunburst(app_id: int, download: bool = Query(False, description="Якщо true – повернути файл як attachment")):
    """Return sunburst HTML visualisation for advanced sentiment. Параметр download дозволяє завантажити файл."""
    try:
        html_path = os.path.join(advanced_insights.get_output_dir(app_id), "advanced_sentiment_sunburst.html")
        if not os.path.exists(html_path):
            raise HTTPException(status_code=404, detail="Sunburst not generated. Call POST /sunburst/{app_id} first.")
        if download:
            filename = os.path.basename(html_path)
            headers = {"Content-Disposition": f"attachment; filename={filename}"}
            return FileResponse(path=html_path, media_type="text/html", headers=headers)
        return FileResponse(path=html_path, media_type="text/html")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sunburst/{app_id}")
def generate_sunburst(app_id: int):
    """Generate sunburst HTML and insights JSON, return HTML."""
    try:
        html_path = _generate_sunburst_html(app_id)
        return FileResponse(path=html_path, media_type="text/html")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 