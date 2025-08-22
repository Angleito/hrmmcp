#!/usr/bin/env python3
"""Test script to verify MCP server starts correctly."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.hrm_mcp_server import HRMServer

async def test_server():
    """Test server initialization."""
    try:
        print("Initializing HRM MCP Server...")
        server = HRMServer()
        await server.initialize()
        print("Server initialized successfully!")
        
        # List tools
        tools_list = await server.mcp.list_tools()
        print(f"Available tools: {[tool.name for tool in tools_list]}")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_server())
    sys.exit(0 if success else 1)