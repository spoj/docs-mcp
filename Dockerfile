FROM python:3.13-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy all source files needed for build
COPY pyproject.toml uv.lock README.md ./
COPY docs_mcp/ ./docs_mcp/

# Install dependencies (needs docs_mcp/ for hatchling to find the package)
RUN uv sync --frozen --no-dev || uv sync --no-dev

# Copy docs directory (override with volume mount for custom docs)
COPY docs/ ./docs/

EXPOSE 8000

CMD ["uv", "run", "docs-mcp"]
