# docs-mcp

Generic documentation MCP server with streamable HTTP transport.

## Quick Start

```bash
# Install
uv sync

# Run (serves docs/ folder by default)
uv run docs-mcp

# Or with custom docs folder
DOCS_DIR=/path/to/your/docs uv run docs-mcp
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCS_DIR` | `./docs` | Path to markdown folder |
| `MCP_NAME` | `docs` | Server name |
| `MCP_API_KEY` | (empty) | API key for auth (empty = no auth) |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Port |

## Tool

### `load_docs(section)`

- `load_docs()` - Returns `INDEX.md` if present, otherwise lists available files
- `load_docs("guide")` or `load_docs("guide.md")` - Returns content of `docs/guide.md`
- `load_docs("api/endpoints")` - Returns content of `docs/api/endpoints.md`

## Deployment

### Docker

```bash
# Build
docker build -t docs-mcp .

# Run with volume mount
docker run -p 8000:8000 -v /path/to/docs:/app/docs docs-mcp

# Or bake docs into image
# Create Dockerfile.custom:
#   FROM docs-mcp
#   COPY my-docs/ /app/docs/
```

### Azure Container Apps

```bash
# Build and push
az acr build --registry <acr> --image docs-mcp:latest .

# Deploy
az containerapp create \
    --name my-docs-mcp \
    --resource-group <rg> \
    --environment <env> \
    --image <acr>.azurecr.io/docs-mcp:latest \
    --target-port 8000 \
    --ingress external \
    --env-vars "MCP_NAME=my-docs" "MCP_API_KEY=secretref:mcp-key" \
    --min-replicas 0 --max-replicas 3
```
