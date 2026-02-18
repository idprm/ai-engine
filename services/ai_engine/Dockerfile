FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject files
COPY pyproject.toml ./
COPY services/ai_engine/pyproject.toml ./services/ai_engine/

# Copy source code (in correct locations for editable install)
# Root package expects shared/ at /app/shared/
COPY shared/ /app/shared/
# AI Engine package expects ai_engine/ at /app/services/ai_engine/ai_engine/
COPY services/ai_engine/src/ai_engine/ /app/services/ai_engine/ai_engine/

# Install Python dependencies
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -e ./services/ai_engine

# Set Python path
ENV PYTHONPATH=/app:/app/shared:/app/services/ai_engine
ENV PYTHONUNBUFFERED=1

# Run the worker
CMD ["python", "-m", "ai_engine.main"]
