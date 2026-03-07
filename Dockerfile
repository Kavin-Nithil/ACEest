# ─────────────────────────────────────────────────────────────────────────────
# ACEest Fitness & Gym — Dockerfile
# Multi-stage: builder installs deps, final image is slim & non-root.
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: dependency builder ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install only what is needed to build Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install into a dedicated prefix so we can copy only the packages later
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: lean runtime image ──────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="ACEest DevOps Team"
LABEL description="ACEest Fitness & Gym Flask API"
LABEL version="1.0.0"

# Security: run as non-root user
RUN groupadd -r aceest && useradd -r -g aceest aceest

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source
COPY app.py .
COPY requirements.txt .

# Change ownership to non-root user
RUN chown -R aceest:aceest /app

USER aceest

# Expose Flask port
EXPOSE 5000

# Health check — calls our /health endpoint every 30 seconds
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" \
    || exit 1

# Production entrypoint using Flask's built-in server
# In production, swap this for: gunicorn -w 4 -b 0.0.0.0:5000 app:app
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]