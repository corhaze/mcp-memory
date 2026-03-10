# Docker

## Build

```bash
docker build -t mcp-memory .
```

## Run the UI server

```bash
# With Docker Compose:
docker compose up

# Without Compose:
docker run --rm -p 7878:7878 -v ~/.mcp-memory:/root/.mcp-memory -e MCP_MEMORY_ENABLE_EMBEDDINGS=1 mcp-memory
```

Open http://localhost:7878 in your browser.

## Connect to Claude Desktop (MCP stdio)

Update `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-memory": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "/Users/YOUR_USERNAME/.mcp-memory:/root/.mcp-memory",
        "-e", "MCP_MEMORY_ENABLE_EMBEDDINGS=1",
        "mcp-memory:latest",
        "uv", "run", "mcp-memory"
      ]
    }
  }
}
```

Replace `YOUR_USERNAME` with your macOS username. The `-i` flag keeps stdin open for stdio transport. The MCP server starts once per Claude session (not per tool call), so the ~1s container startup cost is paid once.

## Why Docker

- The `BAAI/bge-small-en-v1.5` model is pre-baked into the image — semantic search works out of the box with no runtime network access.
- Consistent environment across machines with no local Python setup required.
- The DB always lives on the host via volume mount — data is never stored inside the container.
