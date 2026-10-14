"""Launcher for the MCP server that works from any working directory (MCP clients start it wherever they like).

    /path/to/.venv/bin/python /path/to/scripts/run_mcp.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.mcp_server.server import main  # noqa: E402

if __name__ == "__main__":
    main()
