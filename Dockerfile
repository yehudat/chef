# Dockerfile
FROM python:3.11-slim

# Avoid .pyc and ensure unbuffered output (good for CI logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source tree
COPY . .

# Default command: run chef.py (facade CLI)
CMD ["python", "chef.py"]
