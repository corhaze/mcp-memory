from .mcp import mcp
# Import modules to register tools and resources
from . import projects
from . import tasks
from . import notes
from . import decisions
from . import documents
from . import metadata
from . import search
from . import context
from . import resources

def main():
    import argparse
    parser = argparse.ArgumentParser(description="mcp-memory server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"])
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")

__all__ = ["mcp", "main"]
