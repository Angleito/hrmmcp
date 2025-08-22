#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   Claude Code MCP Configuration Helper${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Get the absolute path of the current directory
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check if Claude config exists
CLAUDE_CONFIG="$HOME/.claude.json"
if [ ! -f "$CLAUDE_CONFIG" ]; then
    echo -e "${YELLOW}Creating new Claude configuration file...${NC}"
    echo '{"mcpServers": {}}' > "$CLAUDE_CONFIG"
fi

# Detect package manager
if command -v uv &> /dev/null && [ -f "$PROJECT_DIR/pyproject.toml" ]; then
    USE_UV="True"
    echo -e "${GREEN}✓ Using uv for package management${NC}"
elif [ -f "$PROJECT_DIR/.venv/bin/python" ]; then
    USE_UV="False"
    echo -e "${GREEN}✓ Using venv Python${NC}"
else
    echo -e "${RED}✗ No virtual environment found. Please run install.sh first.${NC}"
    exit 1
fi

# Create Python script to update the config
cat > /tmp/configure_claude_mcp.py << EOF
import json
import sys

config_file = "$CLAUDE_CONFIG"
project_dir = "$PROJECT_DIR"
use_uv = $USE_UV  # This will be True or False as a Python boolean

# Read existing config
try:
    with open(config_file, 'r') as f:
        config = json.load(f)
except:
    config = {}

# Ensure mcpServers exists
if 'mcpServers' not in config:
    config['mcpServers'] = {}

# Add or update HRM reasoning server
if use_uv:
    config['mcpServers']['hrm-reasoning'] = {
        "command": "uv",
        "args": ["run", "--project", project_dir, "python", "-m", "src.hrm_mcp_server"],
        "cwd": project_dir,
        "env": {
            "PYTHONPATH": project_dir
        }
    }
else:
    config['mcpServers']['hrm-reasoning'] = {
        "command": f"{project_dir}/.venv/bin/python",
        "args": ["-m", "src.hrm_mcp_server"],
        "cwd": project_dir,
        "env": {
            "PYTHONPATH": project_dir
        }
    }

# Write updated config
with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)

print("✓ HRM MCP server added to Claude configuration")
EOF

# Run the Python script
python3 /tmp/configure_claude_mcp.py

# Clean up
rm /tmp/configure_claude_mcp.py

echo ""
echo -e "${GREEN}✓ Configuration updated successfully!${NC}"
echo ""
echo -e "${YELLOW}The HRM MCP server has been added to your Claude configuration.${NC}"
echo ""
echo "Location: $CLAUDE_CONFIG"
echo "Server name: hrm-reasoning"
echo ""
echo -e "${BLUE}Available MCP Tools:${NC}"
echo "  • hierarchical_reason - Complex reasoning with H/L modules"
echo "  • decompose_task - Break down complex tasks"
echo "  • refine_solution - Iteratively improve solutions"
echo "  • analyze_reasoning_trace - Analyze reasoning patterns"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Restart Claude Code (or run /mcp to reload servers)"
echo "2. The HRM reasoning tools will be available automatically"
echo "3. Try: 'Use hierarchical reasoning to solve [your task]'"
echo ""