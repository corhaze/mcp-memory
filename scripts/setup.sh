#!/bin/bash
set -e

# scripts/setup.sh — IDEAL environment initialization for mcp-memory
# If running as an agent and hitting "Operation not permitted", 
# please ask the USER to run this script manually.

PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$PROJECT_ROOT"

echo "🧹 Attempting to clean up redundant environments..."
# .venv is often restricted in agent sandboxes, so we standardize on .venv-mcp
rm -rf .venv .venv2 .venv4 .uv_cache 2>/dev/null || true

echo "📦 Initializing clean .venv-mcp via uv..."
# We use .venv-mcp because .venv is restricted for the agent.
uv venv .venv-mcp

echo "📥 Installing dependencies into .venv-mcp..."
uv pip install -p .venv-mcp -e .
uv pip install -p .venv-mcp pytest ruff

echo "✅ Setup complete!"
echo "Environment standardized on .venv-mcp."
echo "Active with: source .venv-mcp/bin/activate"
