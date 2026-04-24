# ── TN26 Backend ────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy requirements first (for caching)
COPY backend/requirements.txt .

# Install all dependencies in one layer
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/app/   ./app/
COPY backend/train.py ./train.py
COPY backend/data/  ./data/
COPY scraper/       ./scraper/

# Create models directory
RUN mkdir -p /app/models

# Non-root user
RUN useradd -m -u 1000 tn2026user && \
    chown -R tn2026user:tn2026user /app
USER tn2026user

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", \
     "--log-level", "warning"]
