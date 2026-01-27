FROM python:3.12-slim-bookworm

# Install dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy files in order of change frequency
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps

# Copy everything else
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Simple direct command - no shell script, no pipes
CMD ["python", "main.py"]
