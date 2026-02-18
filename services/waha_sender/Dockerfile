FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject files and README
COPY pyproject.toml README.md ./
COPY services/waha_sender/pyproject.toml ./services/waha_sender/

# Copy source code (in correct locations for editable install)
# Root package expects shared/ at /app/shared/
COPY shared/ /app/shared/
# WAHA Sender package expects waha_sender/ at /app/services/waha_sender/waha_sender/
COPY services/waha_sender/src/waha_sender/ /app/services/waha_sender/waha_sender/

# Install Python dependencies
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -e ./services/waha_sender

# Set Python path
ENV PYTHONPATH=/app:/app/shared:/app/services/waha_sender
ENV PYTHONUNBUFFERED=1

# Run the worker
CMD ["python", "-m", "waha_sender.main"]
