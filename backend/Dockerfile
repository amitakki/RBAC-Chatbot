FROM python:3.11-slim

WORKDIR /app
ENV HOME=/home/appuser
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Install uv
RUN pip install --no-cache-dir uv

# Create non-root user
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid 1001 --create-home --home-dir /home/appuser appuser && \
    mkdir -p /opt/venv /app && \
    chown -R appuser:appgroup /home/appuser /opt/venv /app

# Install dependencies first (layer cache)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Download spaCy model needed by Presidio (en_core_web_lg or sm)
RUN python -m spacy download en_core_web_lg

RUN chown -R appuser:appgroup /home/appuser /opt/venv /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
