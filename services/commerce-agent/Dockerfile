# Commerce Agent Worker Dockerfile
# This service runs as a background worker without HTTP endpoints.
# All API routes have been moved to the Gateway service.
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject files and README
COPY pyproject.toml README.md ./
COPY services/commerce-agent/pyproject.toml ./services/commerce-agent/

# Copy source code (in correct locations for editable install)
# Root package expects shared/ at /app/shared/
COPY shared/ /app/shared/
# Commerce Agent package expects commerce_agent/ at /app/services/commerce-agent/commerce_agent/
COPY services/commerce-agent/src/commerce_agent/ /app/services/commerce-agent/commerce_agent/

# Also copy llm-worker for LLM dependencies (LangGraph runner, factory, etc.)
COPY services/llm-worker/pyproject.toml ./services/llm-worker/
COPY services/llm-worker/src/llm_worker/ /app/services/llm-worker/llm_worker/

# Install Python dependencies
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -e ./services/llm-worker && \
    pip install --no-cache-dir -e ./services/commerce-agent

# Set Python path
ENV PYTHONPATH=/app:/app/shared:/app/services/commerce-agent:/app/services/llm-worker
ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME=commerce_agent_worker

# No HTTP port exposed - this is a background worker service

# Health check using Redis ping (worker must be connected to Redis)
# The worker will log its status periodically
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD pgrep -f "commerce_agent.worker" || exit 1

# Run the worker
CMD ["python", "-m", "commerce_agent.worker"]
