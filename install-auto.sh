#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   HRM MCP Server Auto-Installation Script${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Function to check Python version
check_python_version() {
    local python_cmd=$1
    if command -v $python_cmd &> /dev/null; then
        local version=$($python_cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        local major=$(echo $version | cut -d. -f1)
        local minor=$(echo $version | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            echo $python_cmd
            return 0
        fi
    fi
    return 1
}

# Try to find a suitable Python version
echo -e "${YELLOW}Searching for Python 3.11+ ...${NC}"
PYTHON_CMD=""

# Check various Python commands
for cmd in python3.13 python3.12 python3.11 python3 python; do
    if check_python_version $cmd; then
        PYTHON_CMD=$cmd
        break
    fi
done

# Check if uv has its own Python
if [ -z "$PYTHON_CMD" ] && command -v uv &> /dev/null; then
    echo -e "${YELLOW}Checking uv's Python installations...${NC}"
    if [ -d "$HOME/.local/share/uv/python" ]; then
        for python_path in $HOME/.local/share/uv/python/*/bin/python*; do
            if [ -x "$python_path" ] && check_python_version "$python_path"; then
                PYTHON_CMD="$python_path"
                break
            fi
        done
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}✗ No Python 3.11+ found on system${NC}"
    echo ""
    echo -e "${YELLOW}Would you like to install Python 3.12 using uv? (recommended)${NC}"
    echo -e "This will not affect your system Python."
    echo ""
    read -p "Install Python 3.12 with uv? [Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        # Install uv if not present
        if ! command -v uv &> /dev/null; then
            echo -e "${YELLOW}Installing uv...${NC}"
            curl -LsSf https://astral.sh/uv/install.sh | sh
            export PATH="$HOME/.cargo/bin:$PATH"
        fi
        
        # Install Python 3.12
        echo -e "${YELLOW}Installing Python 3.12...${NC}"
        uv python install 3.12
        
        # Find the installed Python
        PYTHON_CMD=$(uv python find 3.12)
        if [ -z "$PYTHON_CMD" ]; then
            echo -e "${RED}Failed to install Python 3.12${NC}"
            exit 1
        fi
        echo -e "${GREEN}✓ Python 3.12 installed successfully${NC}"
    else
        echo -e "${RED}Installation cancelled. Python 3.11+ is required.${NC}"
        echo -e "${YELLOW}Please install Python from:${NC}"
        echo "  • https://python.org (official)"
        echo "  • brew install python@3.12 (macOS)"
        echo "  • apt install python3.12 (Ubuntu/Debian)"
        echo "  • pyenv install 3.12.0 (pyenv)"
        exit 1
    fi
fi

PYTHON_VERSION=$($PYTHON_CMD --version | cut -d' ' -f2)
echo -e "${GREEN}✓ Using Python $PYTHON_VERSION at $PYTHON_CMD${NC}"

# Check for uv (preferred) or pip
echo -e "${YELLOW}Checking package manager...${NC}"
if command -v uv &> /dev/null; then
    PACKAGE_MANAGER="uv"
    echo -e "${GREEN}✓ Using uv (fast Python package manager)${NC}"
else
    PACKAGE_MANAGER="pip"
    echo -e "${GREEN}✓ Using pip${NC}"
fi

# Install dependencies
echo ""
echo -e "${YELLOW}Installing dependencies...${NC}"
if [ "$PACKAGE_MANAGER" = "uv" ]; then
    uv venv .venv --python $PYTHON_CMD 2>/dev/null || true
    uv sync
    echo -e "${GREEN}✓ Dependencies installed with uv${NC}"
else
    # Use pip
    $PYTHON_CMD -m venv .venv
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