# CRM Chatbot Service Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject files and README
COPY pyproject.toml README.md ./
COPY services/crm_chatbot/pyproject.toml ./services/crm_chatbot/

# Copy source code (in correct locations for editable install)
# Root package expects shared/ at /app/shared/
COPY shared/ /app/shared/
# CRM Chatbot package expects crm_chatbot/ at /app/services/crm_chatbot/crm_chatbot/
COPY services/crm_chatbot/src/crm_chatbot/ /app/services/crm_chatbot/crm_chatbot/

# Also copy ai_engine for LLM dependencies (LangGraph runner, factory, etc.)
COPY services/ai_engine/pyproject.toml ./services/ai_engine/
COPY services/ai_engine/src/ai_engine/ /app/services/ai_engine/ai_engine/

# Install Python dependencies
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -e ./services/ai_engine && \
    pip install --no-cache-dir -e ./services/crm_chatbot

# Set Python path
ENV PYTHONPATH=/app:/app/shared:/app/services/crm_chatbot:/app/services/ai_engine
ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME=crm_chatbot

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "crm_chatbot.main:app", "--host", "0.0.0.0", "--port", "8000"]
