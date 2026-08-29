FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=dashboard_app/run.py
ENV PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
COPY dashboard_app/requirements.txt ./dashboard_app/
RUN pip install --no-cache-dir -r dashboard_app/requirements.txt

# Copy the rest of the application
COPY dashboard_app/ ./dashboard_app/
COPY orchestrator/ ./orchestrator/
COPY execution/ ./execution/

# Create instance directory for SQLite if it doesn't exist
RUN mkdir -p dashboard_app/instance

# Entrypoint: applies pending Alembic migrations, then execs whatever CMD/command was given.
# Only the `web` service actually runs this (github-sync overrides its own entrypoint in
# docker-compose.yml to skip it, avoiding two containers migrating the same SQLite file at once).
COPY docker/web/entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Expose port
EXPOSE 5000

# Start the application using gunicorn with gevent for SSE support
CMD ["gunicorn", "--worker-class", "gevent", "--workers", "1", "--bind", "0.0.0.0:5000", "--timeout", "120", "dashboard_app.run:app"]
