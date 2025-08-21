# HRM-Inspired MCP Server

Hierarchical Reasoning Model (HRM) implementation as an MCP server for Claude Code.

## Features

- **Hierarchical reasoning**: H-Module for strategic planning, L-Module for tactical execution
- **Convergence detection**: Local and global convergence with configurable thresholds  
- **State persistence**: SQLite-based session management with automatic cleanup
- **Type safety**: Strict typing with mypy validation
- **Production ready**: Error handling, monitoring, resource limits

## Installation

```bash
uv sync
```

## Usage

Start the MCP server:

```bash
uv run python -m src.hrm_mcp_server
```

## MCP Tools

- `hierarchical_reason`: Main reasoning tool with HRM-inspired approach
- `decompose_task`: Break complex tasks into hierarchical subtasks  
- `refine_solution`: Iteratively improve existing solutions
- `analyze_reasoning_trace`: Analyze reasoning patterns and bottlenecks

## Configuration

Edit `config.yaml` to adjust reasoning parameters, convergence thresholds, and persistence settings.

## Development

```bash
# Type checking
uv run mypy src/

# Tests  
uv run pytest tests/
```