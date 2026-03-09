FROM python:3.12-slim

WORKDIR /app

# Install Node.js (for npx-based MCP servers) and uv/uvx (for uvx-based MCP servers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Backend requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Root-level modules that backend/main.py imports
COPY config.py .
COPY agents/ ./agents/
COPY core/ ./core/
COPY tools/ ./tools/
COPY pipelines/ ./pipelines/

# Backend app files go directly to /app
COPY backend/ ./

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=10s --start-period=60s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
