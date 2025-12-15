# Dockerfile
FROM python:3.11-slim

# Avoid .pyc and ensure unbuffered output (good for CI logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system build dependencies for pyslang.
# pyslang may need a C++, compiler and CMake at build time
# install a minimal set of build tools here.  Remove any unused packages as
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source tree
COPY . .

# Entrypoint: run chef.py (facade CLI)
ENTRYPOINT ["python", "/app/chef.py"]
