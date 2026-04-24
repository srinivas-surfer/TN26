# ── Stage 1: build dependencies ──────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools only in builder stage
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY app/           ./app/
COPY train.py       ./train.py
COPY data/          ./data/

# Create models directory
RUN mkdir -p /app/models

# Non-root user for security (create BEFORE chown)
RUN useradd -m -u 1000 tn2026user && \
    chown -R tn2026user:tn2026user /root/.local && \
    chown -R tn2026user:tn2026user /app
USER tn2026user

# Set PYTHONPATH AFTER user switch - critical!
ENV PYTHONPATH=/root/.local/lib/python3.11/site-packages:/app:$PYTHONPATH \
    PATH=/root/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

EXPOSE 8000

# Single uvicorn worker — t2.micro has 1 vCPU
CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", \
     "--loop", "uvloop", \
     "--log-level", "warning"]
