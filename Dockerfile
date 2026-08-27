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
COPY agents/ ./agents/
COPY main.py .

# Create non-root user for security, with a FIXED uid/gid (1000) that matches
# runAsUser/runAsGroup in k8s/coordinator-deployment.yaml. `useradd -r` (the previous
# version of this line) assigns a system UID from whatever's next free in the image
# (999 here) - not 1000 - so the container was actually running as an unmapped UID
# 1000 that doesn't correspond to this account at all (id shows "uid=1000
# gid=0(root)", not adk-user's 999:999): chown'ing files to adk-user never actually
# granted the running process write access to them.
RUN groupadd -g 1000 adk-user && useradd --no-log-init -u 1000 -g adk-user adk-user
RUN chown -R adk-user:adk-user /app

# get_fast_api_app(web=True) (the /dev-ui console) writes a small runtime-config.json
# into its own package assets at startup so the frontend knows its own base URL. That
# directory is installed system-wide, owned by root (pip ran before USER adk-user
# below) - as our non-root user it failed with "Permission denied", logged as an
# ERROR on every pod start and leaving /dev-ui running on whatever fallback config
# ships in the wheel instead of the one meant for this deployment.
RUN chown -R adk-user:adk-user \
    /usr/local/lib/python3.11/site-packages/google/adk/cli/browser/assets/config

# Create directories for logs and temp files
RUN mkdir -p /app/logs /app/tmp \
    && chown -R adk-user:adk-user /app/logs /app/tmp

# Switch to non-root user
USER adk-user

# Environment variables. No GOOGLE_APPLICATION_CREDENTIALS here - auth is via GKE
# Workload Identity (see k8s/sa.yaml), google-adk/google-genai pick that up through
# Application Default Credentials automatically, no key file needed or wanted.
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port (metrics are mounted on the same port at /metrics, no separate port)
EXPOSE 8080

# Run application
CMD ["python", "main.py"]