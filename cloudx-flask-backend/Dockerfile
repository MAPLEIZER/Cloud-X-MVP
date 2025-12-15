
FROM python:3.9-slim

# Install system dependencies
# nmap: for network scanning
# iputils-ping: for ping command
# curl: for healthchecks/downloads
RUN apt-get update && apt-get install -y \
    nmap \
    iputils-ping \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5001

# Run entrypoint
ENTRYPOINT ["./entrypoint.sh"]
