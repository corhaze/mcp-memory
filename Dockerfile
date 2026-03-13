FROM node:20-slim AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY mcp_memory/ui-src/ ./mcp_memory/ui-src/
RUN npm run build

FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock* ./
COPY mcp_memory/ ./mcp_memory/

# Copy React build output over the ui/ directory
COPY --from=frontend /app/mcp_memory/ui/ ./mcp_memory/ui/

# Install with embeddings (no dev deps)
RUN uv sync --extra embeddings --no-dev

# Pre-download BAAI/bge-small-en-v1.5 at build time
RUN MCP_MEMORY_ENABLE_EMBEDDINGS=1 uv run python -c \
    "from fastembed import TextEmbedding; list(TextEmbedding('BAAI/bge-small-en-v1.5').embed(['warmup']))"

ENV MCP_MEMORY_ENABLE_EMBEDDINGS=1

VOLUME /root/.mcp-memory
EXPOSE 7878

# Default: UI server
CMD ["uv", "run", "uvicorn", "mcp_memory.ui_server:app", \
     "--host", "0.0.0.0", "--port", "7878"]
