# Use a slim Python 3.12 image
FROM python:3.12-slim-bookworm

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system dependencies
# - libpq5: Required for psycopg2-binary
# - fonts-noto-cjk: Required for Japanese, Korean, Chinese support
# - ca-certificates: Required for SSL/TLS
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    fonts-noto-cjk \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files first for caching
COPY pyproject.toml uv.lock ./

# Sync dependencies (including dev if needed, but frozen for production)
RUN uv sync --frozen

# Copy the rest of the application
COPY . .

# Expose the port FastAPI runs on
EXPOSE 8005

# Command to run the application
# We use 'uv run' to ensure the environment is correctly activated
CMD ["uv", "run", "python", "src/main.py"]
