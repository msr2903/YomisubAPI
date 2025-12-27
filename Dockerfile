# =============================================================================
# Yomisub API - Production Dockerfile (UV-optimized)
# =============================================================================
# Optimized for Hugging Face Spaces (Port 7860, Pre-cached Dicts)
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Build environment with uv
# -----------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Install dependencies required for building SudachiPy and downloading dictionaries
# We need curl and tar for the JMDict download script
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    tar \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && rm -rf /var/lib/apt/lists/*

# Add Rust to PATH
ENV PATH="/root/.cargo/bin:$PATH"

# Set environment variables for reproducible builds
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1

# Copy dependency files first
COPY pyproject.toml ./

# Install dependencies into the virtual environment
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python -r pyproject.toml

# Pre-download and cache Sudachi dictionary
RUN /app/.venv/bin/python -c "from sudachipy import Dictionary; Dictionary(dict='full')"

# Copy scripts and download JMDict during build
COPY scripts/ ./scripts/
RUN chmod +x scripts/update_jmdict.sh && ./scripts/update_jmdict.sh

# Copy application source code
COPY src/ ./src/

# -----------------------------------------------------------------------------
# Stage 2: Production runtime (minimal)
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Install minimal runtime dependencies (libgomp1 is needed for some NLP libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security (Hugging Face uses UID 1000)
RUN useradd -m -u 1000 appuser

# Copy virtual environment and files from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/data /app/data

# Set ownership to appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860

# Hugging Face Spaces expects port 7860
EXPOSE 7860

# Health check (using the new port)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:7860/health', timeout=5).raise_for_status()" || exit 1

# Run the FastAPI application
# We use the PORT environment variable so it works on HF (7860) and other platforms
CMD ["sh", "-c", "uvicorn main:app --app-dir src --host 0.0.0.0 --port ${PORT:-7860}"]

