FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject files and README
COPY pyproject.toml README.md ./
COPY services/llm-worker/pyproject.toml ./services/llm-worker/

# Copy source code (in correct locations for editable install)
# Root package expects shared/ at /app/shared/
COPY shared/ /app/shared/
# LLM Worker package expects llm_worker/ at /app/services/llm-worker/llm_worker/
COPY services/llm-worker/src/llm_worker/ /app/services/llm-worker/llm_worker/

# Install Python dependencies
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -e ./services/llm-worker

# Set Python path
ENV PYTHONPATH=/app:/app/shared:/app/services/llm-worker
ENV PYTHONUNBUFFERED=1

# Run the worker
CMD ["python", "-m", "llm_worker.main"]
