FROM python:3.12-slim-trixie

LABEL io.modelcontextprotocol.server.name="io.github.D4Vinci/Scrapling"
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Copy dependency file first for better layer caching
COPY pyproject.toml ./

# Install dependencies only
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --all-extras --compile-bytecode

# Copy source code
COPY . .

# Install browsers and project in one optimized layer
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && \
    uv run playwright install-deps chromium && \
    uv run playwright install chromium && \
    uv sync --all-extras --compile-bytecode && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    chmod -R a+rx /ms-playwright

# Create a non-root user
RUN useradd -m -u 1000 user && \
    chown -R user:user /app

# Switch to the non-root user
USER user

# Expose port for MCP server HTTP transport
EXPOSE 7860

# Set entrypoint to run scrapling
ENTRYPOINT ["uv", "run", "scrapling"]

# Default command (can be overridden)
CMD ["mcp", "--http", "--port", "7860", "--host", "0.0.0.0"]
