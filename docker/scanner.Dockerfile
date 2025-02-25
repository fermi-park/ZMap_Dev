# Use an official Python runtime as a parent image
FROM python:3.11-slim-bullseye

# Set the working directory
WORKDIR /app

# Label maintainer information
LABEL maintainer="your.email@example.com"
LABEL version="1.0"
LABEL description="ZMap network scanner with database integration"

# Create a non-root user for security
RUN groupadd -r zmap && useradd -r -g zmap -m zmap

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    zmap \
    apt-transport-https \
    ca-certificates \
    gnupg \
    curl \
    libgmp10 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    apt-get update && apt-get install -y unzip && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf aws awscliv2.zip && \
    apt-get remove -y unzip && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the application code
COPY Scripts /app/Scripts
COPY lib /app/lib

# Create directories for data and output
RUN mkdir -p /app/data /app/output && \
    chown -R zmap:zmap /app/data /app/output

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app:${PATH}"

# Copy entrypoint script
COPY docker/scanner_entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user for security
USER zmap

# Set volume for data and results
VOLUME ["/app/data", "/app/output"]

# Set default command
ENTRYPOINT ["/app/entrypoint.sh"]