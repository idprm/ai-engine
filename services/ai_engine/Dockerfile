FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
COPY services/ai_engine/pyproject.toml ./services/ai_engine/
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -e ./services/ai_engine

# Copy application code
COPY shared/ /app/shared/
COPY services/ai_engine/src/ai_engine/ /app/ai_engine/

# Set Python path
ENV PYTHONPATH=/app:/app/shared
ENV PYTHONUNBUFFERED=1

# Run the worker
CMD ["python", "-m", "ai_engine.main"]
