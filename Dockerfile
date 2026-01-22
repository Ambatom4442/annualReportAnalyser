# =============================================================================
# Annual Report Analyser - Docker Configuration
# Uses Playwright base image for browser automation support
# =============================================================================

# Stage 1: Base image with Playwright browsers pre-installed
FROM mcr.microsoft.com/playwright/python:v1.49.1-noble

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    # uv settings
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    # Streamlit settings
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Set working directory
WORKDIR /app

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first (for better layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source code
COPY src/ ./src/
COPY main.py ./
COPY .python-version ./
COPY .streamlit/ ./.streamlit/

# Create data directories with proper permissions
RUN mkdir -p /app/.data /app/.data/chroma_db /app/.data/documents && \
    chmod -R 777 /app/.data

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run the application using uv
CMD ["uv", "run", "streamlit", "run", "src/app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--browser.gatherUsageStats=false"]
