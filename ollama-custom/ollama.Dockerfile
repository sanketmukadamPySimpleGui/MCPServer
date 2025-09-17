# ollama.Dockerfile
FROM ollama/ollama:latest

# Install curl (and any other tools you need)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# No need to create or switch users — the container runs as root by default

