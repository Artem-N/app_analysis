FROM python:3.10-slim

# System packages that may be required for building wheels (e.g. numpy, pandas)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Install Python dependencies first to leverage Docker layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application source code
COPY . .

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Start the FastAPI app using Uvicorn
CMD ["uvicorn", "api_main:app", "--host", "0.0.0.0", "--port", "8080"]