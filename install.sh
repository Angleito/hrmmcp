#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   HRM MCP Server Installation Script${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
    
    # Check if Python 3.11+ is installed (required for security and MCP compatibility)
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]); then
        echo -e "${RED}✗ Python 3.11+ is required for security. Current version: $PYTHON_VERSION${NC}"
        echo -e "${YELLOW}Please install Python 3.11 or higher from https://python.org${NC}"
        echo -e "${YELLOW}Or use pyenv/conda to manage Python versions${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Python3 not found. Please install Python 3.11 or higher.${NC}"
    exit 1
fi

# Check for uv (preferred) or pip
echo -e "${YELLOW}Checking package manager...${NC}"
if command -v uv &> /dev/null; then
    PACKAGE_MANAGER="uv"
    echo -e "${GREEN}✓ Using uv (fast Python package manager)${NC}"
elif command -v pip3 &> /dev/null; then
    PACKAGE_MANAGER="pip"
    echo -e "${GREEN}✓ Using pip${NC}"
else
    echo -e "${RED}✗ No Python package manager found. Please install uv or pip.${NC}"
    echo -e "${YELLOW}  To install uv: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    exit 1
fi

# Install dependencies
echo ""
echo -e "${YELLOW}Installing dependencies...${NC}"
if [ "$PACKAGE_MANAGER" = "uv" ]; then
    uv venv .venv 2>/dev/null || true
    uv sync
    echo -e "${GREEN}✓ Dependencies installed with uv${NC}"
else
    # Use pip
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt || pip install mcp pydantic aiosqlite pyyaml
    echo -e "${GREEN}✓ Dependencies installed with pip${NC}"
fi

# Create default config if it doesn't exist
if [ ! -f "config.yaml" ]; then
    echo -e "${YELLOW}Creating default configuration...${NC}"
    cat > config.yaml << 'EOF'
server:
  max_concurrent_sessions: 10
  session_timeout_minutes: 30

reasoning:
  h_module:
    max_iterations: 10
    min_confidence_threshold: 0.7
  l_module:
    max_cycles_per_h: 6
    min_cycles_per_h: 3
  convergence:
    global_threshold: 0.85

persistence:
  database_path: "hrm_reasoning.db"
  retention_days: 7
EOF
    echo -e "${GREEN}✓ Created config.yaml${NC}"
fi

# Test the installation
echo ""
echo -e "${YELLOW}Testing installation...${NC}"
if [ "$PACKAGE_MANAGER" = "uv" ]; then
    TEST_OUTPUT=$(echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "1.0.0", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}, "id": 1}' | uv run python -m src.hrm_mcp_server 2>/dev/null | head -1)
else
    TEST_OUTPUT=$(echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "1.0.0", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}, "id": 1}' | .venv/bin/python -m src.hrm_mcp_server 2>/dev/null | head -1)
fi

if echo "$TEST_OUTPUT" | grep -q '"result"'; then
    echo -e "${GREEN}✓ Server test successful!${NC}"
else
    echo -e "${RED}✗ Server test failed. Please check the installation.${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   Installation Complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo "1. Add the server to your Claude Code configuration:"
echo ""
if [ "$PACKAGE_MANAGER" = "uv" ]; then
    echo "   Run: ${GREEN}./configure-claude.sh${NC}"
else
    echo "   Run: ${GREEN}python3 configure_claude.py${NC}"
fi
echo ""
echo "2. Or manually add to ~/.claude.json:"
echo ""
echo '   "hrm-reasoning": {'
if [ "$PACKAGE_MANAGER" = "uv" ]; then
    echo '     "command": "uv",'
    echo '     "args": ["run", "--project", "'$(pwd)'", "python", "-m", "src.hrm_mcp_server"],'
else
    echo '     "command": "'$(pwd)'/.venv/bin/python",'
    echo '     "args": ["-m", "src.hrm_mcp_server"],'
fi
echo '     "cwd": "'$(pwd)'"'
echo '   }'
echo ""
echo "3. Restart Claude Code to load the new MCP server"
echo ""
echo -e "${GREEN}Available MCP tools:${NC}"
echo "  • hierarchical_reason - Complex reasoning with H/L modules"
echo "  • decompose_task - Break down complex tasks"
echo "  • refine_solution - Iteratively improve solutions"
echo "  • analyze_reasoning_trace - Analyze reasoning patterns"
echo ""