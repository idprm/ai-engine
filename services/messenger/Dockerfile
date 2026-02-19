FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject files and README
COPY pyproject.toml README.md ./
COPY services/messenger/pyproject.toml ./services/messenger/

# Copy source code (in correct locations for editable install)
# Root package expects shared/ at /app/shared/
COPY shared/ /app/shared/
# Messenger package expects messenger/ at /app/services/messenger/messenger/
COPY services/messenger/src/messenger/ /app/services/messenger/messenger/

# Install Python dependencies
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -e ./services/messenger

# Set Python path
ENV PYTHONPATH=/app:/app/shared:/app/services/messenger
ENV PYTHONUNBUFFERED=1

# Run the worker
CMD ["python", "-m", "messenger.main"]
