# This Dockerfile sets up a minimal Python environment to run the server.

# Start with a modern Node.js base image.
FROM node:18-slim

# Install Python and its package manager (pip).
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    curl \
    ca-certificates \
    openssl \
    libssl-dev \
    libffi-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory for the application files.
WORKDIR /app

# Copy the requirements file into the container.
COPY requirements.txt .

# Install Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt --break-system-packages

# Copy the rest of the application files.
COPY . /app

# Expose port for the server.
EXPOSE 8000

# Set the command to run the Python server directly.
CMD ["python3", "fastmcp_quickstart.py", "--transport", "sse", "--host", "0.0.0.0", "--port", "8000"]