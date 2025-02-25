# Use an official Python runtime as a parent image
FROM python:3.11-slim-bullseye

# Set the working directory
WORKDIR /app

# Label maintainer information
LABEL maintainer="your.email@example.com"
LABEL version="1.0"
LABEL description="API for ZMap scanner results"

# Create a non-root user for security
RUN groupadd -r zmap && useradd -r -g zmap -m zmap

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY api-requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the API code
COPY api /app/api
COPY lib /app/lib

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Copy entrypoint script
COPY docker/api_entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user for security
USER zmap

# Expose the API port
EXPOSE 8000

# Set default command
ENTRYPOINT ["/app/entrypoint.sh"]