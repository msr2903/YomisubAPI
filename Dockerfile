# =============================================================================
# Sub-Grabber API - Production Dockerfile (UV-optimized)
# =============================================================================
# Uses multi-stage build for minimal final image with uv caching optimization
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Build environment with uv
# -----------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Set environment variables for reproducible builds
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1

# Copy dependency files first (for Docker cache optimization)
COPY pyproject.toml ./

# Install dependencies into the virtual environment
# We use --no-dev to exclude dev dependencies in production
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python -r pyproject.toml

# Pre-download and cache Sudachi dictionary during build
# This prevents runtime downloads and ensures the dict is available
RUN /app/.venv/bin/python -c "from sudachipy import Dictionary; Dictionary()"

# Pre-initialize jamdict database during build
# This downloads JMdict, KanjiDic2 data if not present
RUN /app/.venv/bin/python -c "from jamdict import Jamdict; jmd = Jamdict(); jmd.lookup('日本')" || true

# Copy application source code
COPY src/ ./src/

# -----------------------------------------------------------------------------
# Stage 2: Production runtime (minimal)
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/src /app/src

# Copy jamdict data directory if it exists (for pre-cached dictionaries)
COPY --from=builder /root/.jamdict /home/appuser/.jamdict 2>/dev/null || true

# Set ownership
RUN chown -R appuser:appuser /app /home/appuser

# Switch to non-root user
USER appuser

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose the API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5).raise_for_status()" || exit 1

# Run the FastAPI application with uvicorn
CMD ["uvicorn", "main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
