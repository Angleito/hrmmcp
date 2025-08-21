# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is an MCP (Model Context Protocol) server implementing Hierarchical Reasoning Model (HRM) with dual-module architecture:

- **H-Module** (`reasoning_engine.py:HModule`): Strategic planning, problem decomposition, high-level decisions
- **L-Module** (`reasoning_engine.py:LModule`): Tactical execution, local optimizations, iterative refinement
- **State Management** (`state_manager.py`): SQLite-based persistence with session lifecycle management
- **Convergence Detection** (`convergence.py`): Local and global convergence monitoring

## Development Commands

```bash
# Start MCP server
uv run python -m src.hrm_mcp_server

# Type checking (REQUIRED after every edit)
uv run mypy src/

# Run tests
uv run pytest tests/

# Install dependencies
uv sync
```

## Core Principles

**EDIT FIRST, CREATE NEVER**: Always prefer editing existing files. Only create new files when absolutely necessary.

**MINIMAL DIFFS**: Achieve solutions with the fewest possible changes. Every edit must be essential.

**EVERY LINE MATTERS**: No redundant code. Every line must be crucial and needed.

## Python Standards

### Package Management
- Use `uv` for all Python package management
- Commands: `uv add`, `uv remove`, `uv sync`, `uv run`

### Type System
```python
# REQUIRED: Strict typing for all functions, variables, and return types
def process_data(items: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    return result
```

### Code Structure
- **Functions**: Max 10 lines, single responsibility
- **Modules**: Separate concerns strictly
- **Classes**: Only when state management is essential
- **Imports**: Grouped (standard, third-party, local) with minimal imports

## Quality Gates

### Mandatory After Every Edit
```bash
# Run type checker
uv run mypy .
# Or if using pyright
uv run pyright .
```

### Security First
- No hardcoded secrets or credentials
- Input validation on all external data
- Proper error handling without information leakage
- Production-ready code only (no mocks/simulations)

## MCP Tools Architecture

The server exposes 4 main MCP tools in `tools.py`:

- `hierarchical_reason`: Primary reasoning tool using dual H/L-module approach
- `decompose_task`: Break complex tasks into hierarchical subtasks
- `refine_solution`: Iteratively improve existing solutions with specific goals
- `analyze_reasoning_trace`: Post-hoc analysis of reasoning patterns and performance

## Key Configuration Files

- `config.yaml`: Runtime parameters for H/L-modules, convergence thresholds, persistence settings
- `pyproject.toml`: Dependencies, mypy strict typing configuration, pytest settings

## Development Workflow

1. **Search First**: Use Qdrant MCP to understand codebase before changes
2. **Edit Minimally**: Find existing code to modify rather than create
3. **Type Check**: Run `uv run mypy src/` after every file modification
4. **Test Locally**: Ensure functionality before proceeding

## Session Management Patterns

- Sessions are created via `HRMServer.create_session()` with UUID tracking
- State persistence through `StateManager` with SQLite backend
- Automatic cleanup of expired sessions (configurable retention period)
- Session status lifecycle: `ACTIVE` → `COMPLETED`/`TIMEOUT`/`ERROR`

## Naming Conventions
- Variables: `snake_case` (concise but descriptive)
- Functions: `snake_case` (verb-based)
- Classes: `PascalCase` (noun-based)
- Constants: `UPPER_SNAKE_CASE`

## Error Handling
```python
# Concise, informative, secure
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {type(e).__name__}")
    raise ProcessingError("Unable to process request") from e
```

## File Organization
- Flat structure when possible
- Group related functionality in modules
- No deep nesting (max 3 levels)

**REMEMBER**: Code quality over quantity. Less code that works perfectly is better than more code that works adequately.