# Google ADK Travel System - Production Dockerfile
FROM python:3.11-slim

# Metadata
LABEL maintainer="ADK Travel Team" \
      version="1.0" \
      description="Google ADK Travel System with Vertex AI and Gemini"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY main.py .

# Create non-root user for security
RUN groupadd -r adk-user && useradd --no-log-init -r -g adk-user adk-user
RUN chown -R adk-user:adk-user /app

# Create directories for logs and temp files
RUN mkdir -p /app/logs /app/tmp \
    && chown -R adk-user:adk-user /app/logs /app/tmp

# Switch to non-root user
USER adk-user

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV GOOGLE_APPLICATION_CREDENTIALS=/var/secrets/google/service-account-key

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose ports
EXPOSE 8080 8090

# Run application
CMD ["python", "main.py"]