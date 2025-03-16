# Dockerfile
FROM python:3.11.7-slim AS python3_11_base

# Update pip
RUN pip install --upgrade pip 

# Set work directory
WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    pkg-config \
    curl \
    cron \
    && apt-get clean