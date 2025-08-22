# HRM-Inspired MCP Server

An MCP (Model Context Protocol) server implementing Hierarchical Reasoning Model inspired by DeepMind's research on hierarchical problem-solving and dual-system reasoning.

## 🚀 Quick Start

### Installation (3 Simple Steps)

```bash
# 1. Clone the repository
git clone https://github.com/Angleito/hrmmcp.git
cd hrmmcp

# 2. Install dependencies (auto-detects Python)
chmod +x install-auto.sh
./install-auto.sh

# 3. Configure Claude Code
chmod +x configure-claude.sh
./configure-claude.sh
```

**That's it!** Restart Claude Code and the HRM reasoning tools will be available.

> **Don't have Python 3.11+?** The `install-auto.sh` script will help you install it automatically using `uv`.

## 📦 Alternative Installation Methods

### Method 1: Using Python directly

```bash
# Install with pip
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure Claude
python3 configure_claude.py
```

### Method 2: Manual Configuration

1. Install dependencies:
```bash
uv sync  # or: pip install mcp pydantic aiosqlite pyyaml
```

2. Add to `~/.claude.json`:
```json
{
  "mcpServers": {
    "hrm-reasoning": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/hrmmcp", "python", "-m", "src.hrm_mcp_server"],
      "cwd": "/path/to/hrmmcp"
    }
  }
}
```

### Method 3: Project-level Configuration

The repository includes `.mcp.json` for automatic project-level configuration. When you open this project in Claude Code, it will automatically detect and use the HRM MCP server.

## 🛠️ MCP Tools

Once installed, these tools are available in Claude Code:

- **`hierarchical_reason`** - Main reasoning tool using dual H/L-module approach
  - Strategic planning with H-Module
  - Tactical execution with L-Module
  - Automatic convergence detection
  
- **`decompose_task`** - Break complex tasks into hierarchical subtasks
  - Intelligent task decomposition
  - Dependency tracking
  - Complexity estimation
  
- **`refine_solution`** - Iteratively improve existing solutions
  - Goal-directed refinement
  - Convergence monitoring
  - Quality metrics
  
- **`analyze_reasoning_trace`** - Analyze reasoning patterns and bottlenecks
  - Performance analysis
  - Pattern recognition
  - Optimization suggestions

## 💡 Usage Examples

In Claude Code, you can use natural language:

```
"Use hierarchical reasoning to design a REST API for a library management system"

"Decompose the task of building a real-time chat application"

"Refine this solution to improve performance and maintainability"

"Analyze the reasoning trace for implementing a caching system"
```

## ⚙️ Configuration

Edit `config.yaml` to customize:

```yaml
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
```

## 🧪 Development

### Type Checking
```bash
uv run mypy src/
```

### Running Tests
```bash
uv run pytest tests/ -v
```

### Manual Testing
```bash
# Test the MCP server
echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "1.0.0", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}, "id": 1}' | uv run python -m src.hrm_mcp_server
```

## 📋 Requirements

- **Python 3.11+** (required for security and MCP compatibility)
- Claude Code (with MCP support)
- uv (recommended) or pip

> **Security Note**: Python 3.11+ is required for the latest security patches and full MCP protocol support. Older versions may have known vulnerabilities.

## 🏗️ Architecture

The HRM MCP server implements a dual-module architecture:

- **H-Module (Strategic)**: High-level planning, goal decomposition, strategic decisions
- **L-Module (Tactical)**: Low-level execution, local optimizations, iterative refinement
- **Convergence Detection**: Monitors both local and global convergence
- **State Management**: SQLite-based persistence with session lifecycle management

## 📄 License

MIT

## 🤝 Contributing

Contributions are welcome! Please ensure:
- All tests pass (`uv run pytest`)
- Type checking passes (`uv run mypy src/`)
- Code follows existing patterns

## 🐛 Troubleshooting

### Server won't connect in Claude Code

1. Check installation: `./install.sh`
2. Verify configuration: `cat ~/.claude.json | grep hrm-reasoning`
3. Test manually: `uv run python -m src.hrm_mcp_server`
4. Restart Claude Code

### Dependencies issues

```bash
# Clean install
rm -rf .venv
./install.sh
```

### Permission denied

```bash
chmod +x install.sh configure-claude.sh
```

## 📚 Learn More

- [MCP Documentation](https://modelcontextprotocol.io)
- [Claude Code Docs](https://docs.anthropic.com/en/docs/claude-code)
- [HRM Research Paper](https://arxiv.org/abs/hierarchical-reasoning)