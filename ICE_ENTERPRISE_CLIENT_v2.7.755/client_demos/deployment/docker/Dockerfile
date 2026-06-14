FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Copy and install local dependency
COPY RAG-Anything /app/RAG-Anything
RUN pip install --no-cache-dir ./RAG-Anything

# Copy the rest of the application
COPY . .

# Pre-download models to avoid race conditions in multi-worker setup
RUN python scripts/download_models.py

# Install the package in editable mode if needed, or just ensure ice is in PYTHONPATH
ENV PYTHONPATH=/app

# Expose the engine port
EXPOSE 8000

# Start command: run setup then start uvicorn with worker count
CMD python ice/setup_db.py && uvicorn ice.main:app --host 0.0.0.0 --port 8000 --workers ${ICE_WORKERS:-1} --loop asyncio --http h11
