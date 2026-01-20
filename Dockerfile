FROM python:3.13-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml ./
COPY README.md ./

# Install dependencies
RUN uv sync --frozen --no-dev || uv sync --no-dev

# Copy application code
COPY docs_mcp/ ./docs_mcp/

# Copy docs directory (override with volume mount for custom docs)
COPY docs/ ./docs/

EXPOSE 8000

CMD ["uv", "run", "docs-mcp"]
