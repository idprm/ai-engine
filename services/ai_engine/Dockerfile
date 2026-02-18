FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject files
COPY pyproject.toml ./
COPY services/ai_engine/pyproject.toml ./services/ai_engine/

# Copy source code FIRST (required for editable install)
COPY shared/ /app/shared/
COPY services/ai_engine/src/ai_engine/ /app/ai_engine/

# Install Python dependencies
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -e ./services/ai_engine

# Set Python path
ENV PYTHONPATH=/app:/app/shared
ENV PYTHONUNBUFFERED=1

# Run the worker
CMD ["python", "-m", "ai_engine.main"]
