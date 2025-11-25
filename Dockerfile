# Use official Python base image
FROM python:3.12.4-slim

# Set working directory
WORKDIR /app

# Install system dependencies (optional: for things like psycopg2, Pillow, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libgl1 \
    libglib2.0-0 \
    git \
    curl \
    libmupdf-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv or requirements.txt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy FastAPI app
COPY . .

# Expose FastAPI default port
EXPOSE 8000

# Run app with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
