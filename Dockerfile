# Use the official, lightweight Python image
FROM python:3.11-slim

# Stop Python from generating .pyc files and enable live logging
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create a folder inside the container for your app
WORKDIR /app

# Install system dependencies required for psycopg2 (PostgreSQL) and Pandas
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy your requirements file and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your project files into the container
COPY . .