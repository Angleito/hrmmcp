#!/usr/bin/env python3
"""Configure Claude Code to use the HRM MCP server."""

import json
import os
import sys
from pathlib import Path

# Colors for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
NC = '\033[0m'  # No Color

def print_header():
    """Print a nice header."""
    print(f"{BLUE}{'='*65}{NC}")
    print(f"{GREEN}   Claude Code MCP Configuration Helper{NC}")
    print(f"{BLUE}{'='*65}{NC}")
    print()

def check_installation():
    """Check if the server is properly installed."""
    project_dir = Path(__file__).parent.absolute()
    
    # Check for uv
    has_uv = os.system("which uv > /dev/null 2>&1") == 0
    
    # Check for venv
    venv_path = project_dir / ".venv" / "bin" / "python"
    has_venv = venv_path.exists()
    
    if not has_uv and not has_venv:
        print(f"{RED}✗ No installation found. Please run install.sh first.{NC}")
        sys.exit(1)
    
    return project_dir, has_uv, venv_path

def update_claude_config(project_dir, has_uv, venv_path):
    """Update the Claude configuration file."""
    config_file = Path.home() / ".claude.json"
    
    # Read or create config
    if config_file.exists():
        with open(config_file, 'r') as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                print(f"{YELLOW}Warning: Existing config is invalid. Creating new one.{NC}")
                config = {}
    else:
        print(f"{YELLOW}Creating new Claude configuration file...{NC}")
        config = {}
    
    # Ensure mcpServers exists
    if 'mcpServers' not in config:
        config['mcpServers'] = {}
    
    # Configure based on available package manager
    if has_uv:
        print(f"{GREEN}✓ Configuring with uv{NC}")
        config['mcpServers']['hrm-reasoning'] = {
            "command": "uv",
            "args": ["run", "--project", str(project_dir), "python", "-m", "src.hrm_mcp_server"],
            "cwd": str(project_dir),
            "env": {
                "PYTHONPATH": str(project_dir)
            }
        }
    else:
        print(f"{GREEN}✓ Configuring with venv{NC}")
        config['mcpServers']['hrm-reasoning'] = {
            "command": str(venv_path),
            "args": ["-m", "src.hrm_mcp_server"],
            "cwd": str(project_dir),
            "env": {
                "PYTHONPATH": str(project_dir)
            }
        }
    
    # Write config
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    return config_file

def print_success(config_file):
    """Print success message and next steps."""
    print()
    print(f"{GREEN}✓ Configuration updated successfully!{NC}")
    print()
    print(f"{YELLOW}The HRM MCP server has been added to your Claude configuration.{NC}")
    print()
    print(f"Location: {config_file}")
    print(f"Server name: hrm-reasoning")
    print()
    print(f"{BLUE}Available MCP Tools:{NC}")
    print("  • hierarchical_reason - Complex reasoning with H/L modules")
    print("  • decompose_task - Break down complex tasks")
    print("  • refine_solution - Iteratively improve solutions")
    print("  • analyze_reasoning_trace - Analyze reasoning patterns")
    print()
    print(f"{YELLOW}Next steps:{NC}")
    print("1. Restart Claude Code (or run /mcp to reload servers)")
    print("2. The HRM reasoning tools will be available automatically")
    print("3. Try: 'Use hierarchical reasoning to solve [your task]'")
    print()

def main():
    """Main configuration function."""
    print_header()
    
    # Check installation
    project_dir, has_uv, venv_path = check_installation()
    
    # Update configuration
    config_file = update_claude_config(project_dir, has_uv, venv_path)
    
    # Print success
    print_success(config_file)

if __name__ == "__main__":
    main()