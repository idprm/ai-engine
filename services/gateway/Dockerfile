FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
COPY services/gateway/pyproject.toml ./services/gateway/
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -e ./services/gateway

# Copy application code
COPY shared/ /app/shared/
COPY services/gateway/src/gateway/ /app/gateway/

# Set Python path
ENV PYTHONPATH=/app:/app/shared
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
