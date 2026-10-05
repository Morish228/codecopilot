FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files first to cache layers
COPY pyproject.toml uv.lock README.md ./

# Copy application source code
COPY src/ src/

# Install dependencies in the system environment
RUN uv pip install --system .

# Copy static assets and other configs
COPY web/ web/
COPY routing.config.json routing.config.gemini.json ./

# Expose server port
EXPOSE 8000

# Set Python encoding environment variable to handle terminal output correctly
ENV PYTHONIOENCODING=utf-8

# Run the backend FastAPI server
CMD ["python", "-m", "coding_assistant", "serve", "--host", "0.0.0.0", "--port", "8000"]
