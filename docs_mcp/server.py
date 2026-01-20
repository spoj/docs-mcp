"""Generic Docs MCP Server - Streamable HTTP transport."""

import os
import re
from pathlib import Path

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount

# Configuration from environment
DOCS_DIR = Path(os.getenv("DOCS_DIR", "docs")).resolve()
MCP_NAME = os.getenv("MCP_NAME", "docs")
MCP_API_KEY = os.getenv("MCP_API_KEY", "")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Initialize FastMCP
mcp = FastMCP(
    MCP_NAME,
    stateless_http=True,
    json_response=True,
    host=HOST,
    port=PORT,
)


def _list_docs() -> list[str]:
    """List all markdown files in DOCS_DIR recursively."""
    if not DOCS_DIR.exists():
        return []
    docs = []
    for p in DOCS_DIR.rglob("*.md"):
        rel = p.relative_to(DOCS_DIR)
        docs.append(str(rel))
    return sorted(docs)


def _resolve_section(section: str) -> Path | None:
    """Resolve section name to file path, with security checks."""
    # Normalize: add .md if missing
    if not section.endswith(".md"):
        section = section + ".md"

    target = (DOCS_DIR / section).resolve()

    # Security: ensure target is within DOCS_DIR
    try:
        target.relative_to(DOCS_DIR)
    except ValueError:
        return None

    if target.exists() and target.is_file():
        return target
    return None


@mcp.tool()
def load_docs(section: str = "") -> str:
    """Load a documentation section.

    Args:
        section: Path to doc file (e.g. "guide" or "api/endpoints.md").
                 Empty returns INDEX.md if present, otherwise lists available sections.

    Returns:
        The documentation content or list of available sections.
    """
    section = section.strip()

    # No section specified
    if not section:
        # Check for INDEX.md
        index_path = DOCS_DIR / "INDEX.md"
        if index_path.exists():
            return index_path.read_text(encoding="utf-8")
        # Otherwise list available docs
        docs = _list_docs()
        if not docs:
            return "No documentation files found."
        return "Available sections:\n" + "\n".join(f"- {d}" for d in docs)

    # Resolve and read the section
    path = _resolve_section(section)
    if path is None:
        docs = _list_docs()
        return f"Section '{section}' not found.\n\nAvailable sections:\n" + "\n".join(
            f"- {d}" for d in docs
        )

    return path.read_text(encoding="utf-8")


@mcp.tool()
def grep_docs(pattern: str, include: str = "*.md") -> str:
    """Search documentation content using regex.

    Args:
        pattern: Regex pattern to search for (e.g. "error.*handling", "def\\s+\\w+").
        include: Glob pattern to filter files (default "*.md", e.g. "api/*.md").

    Returns:
        Matching file paths with line numbers and content, sorted by file path.
    """
    if not DOCS_DIR.exists():
        return "No documentation directory found."

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return f"Invalid regex pattern: {e}"

    # Find matching files
    matches: list[tuple[str, int, str]] = []  # (file, line_num, line_content)

    for path in sorted(DOCS_DIR.rglob(include)):
        if not path.is_file():
            continue

        # Security: ensure within DOCS_DIR
        try:
            rel_path = path.relative_to(DOCS_DIR)
        except ValueError:
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            if regex.search(line):
                matches.append((str(rel_path), line_num, line.strip()))

    if not matches:
        return f"No matches found for pattern '{pattern}' in {include}"

    # Format output like OpenCode grep: file:line_num:content
    results = []
    for file, line_num, content in matches[:100]:  # Limit to 100 matches
        # Truncate long lines
        if len(content) > 200:
            content = content[:200] + "..."
        results.append(f"{file}:{line_num}: {content}")

    output = "\n".join(results)
    if len(matches) > 100:
        output += f"\n\n... and {len(matches) - 100} more matches"

    return output


# --- Auth middleware ---
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth for health endpoint
        if request.url.path == "/health":
            return await call_next(request)

        # No auth if key not set
        if not MCP_API_KEY:
            return await call_next(request)

        # Check Authorization: Bearer <token>
        auth_header = request.headers.get("Authorization", "")
        if auth_header == f"Bearer {MCP_API_KEY}":
            return await call_next(request)

        # Check x-api-key header
        api_key = request.headers.get("x-api-key", "")
        if api_key == MCP_API_KEY:
            return await call_next(request)

        return JSONResponse({"error": "Unauthorized"}, status_code=401)


async def health(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok", "server": MCP_NAME, "docs_dir": str(DOCS_DIR)})


def create_app() -> Starlette:
    """Create Starlette app with health endpoint and optional auth."""
    from contextlib import asynccontextmanager

    from starlette.routing import Route

    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app):
        async with mcp_app.router.lifespan_context(app):
            yield

    middlewares = [Middleware(AuthMiddleware)] if MCP_API_KEY else []

    return Starlette(
        routes=[
            Route("/health", health, methods=["GET"]),
            Mount("/", app=mcp_app),
        ],
        middleware=middlewares,
        lifespan=lifespan,
    )


def main():
    """Run the MCP server."""
    print(f"Starting {MCP_NAME} MCP server")
    print(f"Docs directory: {DOCS_DIR}")
    print(f"Auth: {'enabled' if MCP_API_KEY else 'disabled (dev mode)'}")

    uvicorn.run(create_app(), host=HOST, port=PORT)


if __name__ == "__main__":
    main()
