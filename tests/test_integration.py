"""Integration tests that verify actual HRM reasoning functionality works correctly."""

import asyncio
import os
import tempfile
import pytest
from pathlib import Path
from typing import Any, Dict

from src.hrm_mcp_server import HRMServer
from src.reasoning_engine import ReasoningEngine
from src.models import SessionStatus


@pytest.fixture
async def isolated_server():
    """Create server with isolated temporary database."""
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_db_path = tmp.name
    
    # Create custom config content
    config_content = f"""
server:
  max_concurrent_sessions: 3
  session_timeout_minutes: 30
persistence:
  database_path: "{tmp_db_path}"
reasoning:
  h_module:
    max_iterations: 10
    min_confidence_threshold: 0.7
  l_module:
    max_cycles_per_h: 6
    min_cycles_per_h: 3
  convergence:
    global_threshold: 0.85
"""
    
    # Write config to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as config_file:
        config_file.write(config_content)
        config_path = config_file.name
    
    try:
        # Create server with isolated config
        server = HRMServer(Path(config_path))
        await server.initialize()
        yield server
    finally:
        # Cleanup
        try:
            os.unlink(config_path)
            os.unlink(tmp_db_path)
        except FileNotFoundError:
            pass  # Already cleaned up


class TestHRMReasoningIntegration:
    """Test actual reasoning capabilities with realistic tasks."""
    
    @pytest.mark.asyncio
    async def test_hierarchical_decomposition_produces_valid_subtasks(self) -> None:
        """Verify that task decomposition creates logically coherent subtasks."""
        engine = ReasoningEngine()
        
        # Test with a complex but well-defined task
        task = "Design and implement a thread-safe cache with TTL expiration"
        
        engine.h_module.initialize_problem(task, {})
        goals = engine.h_module.state.pending_subgoals
        
        # Property: Should decompose into multiple logical subtasks
        assert len(goals) >= 3, f"Complex task should decompose into multiple subtasks, got {len(goals)}"
        
        # Property: Each subtask should be more specific than original
        for goal in goals:
            assert len(goal.description) > 10, "Subtasks should be descriptive"
            assert goal.description.lower() != task.lower(), "Subtasks should differ from original"
            
        # Property: Subtasks should relate to the original domain
        task_keywords = {"cache", "thread", "ttl", "expir", "design", "implement"}
        for goal in goals:
            has_related_keyword = any(keyword in goal.description.lower() for keyword in task_keywords)
            assert has_related_keyword, f"Subtask '{goal.description}' should relate to original task"
    
    @pytest.mark.asyncio
    async def test_reasoning_engine_produces_coherent_solutions(self) -> None:
        """Test that reasoning engine produces solutions that make logical sense."""
        engine = ReasoningEngine()
        
        task = "Implement a function to validate email addresses"
        context = {"language": "python", "requirements": ["RFC compliant", "handle edge cases"]}
        
        result = await engine.reason(
            task=task,
            context=context,
            max_h_iterations=3,
            max_l_cycles=4,
            convergence_threshold=0.7
        )
        
        # Property: Solution should exist and be structured
        assert "solution" in result
        assert isinstance(result["solution"], dict)
        assert len(result["solution"]) > 0
        
        # Property: Should have reasoning trace with actual steps
        trace = result["reasoning_trace"]
        assert len(trace) > 0, "Should have reasoning steps"
        
        # Property: Confidence should be reasonable for a well-defined task
        confidence = result["metadata"]["confidence_score"]
        assert 0.0 <= confidence <= 1.0, f"Confidence {confidence} should be in [0,1]"
        assert confidence > 0.3, "Should have reasonable confidence for clear task"
    
    @pytest.mark.asyncio 
    async def test_convergence_behavior_with_impossible_task(self) -> None:
        """Verify that system handles impossible/contradictory tasks appropriately."""
        engine = ReasoningEngine()
        
        # Deliberately impossible task
        task = "Create a function that returns both True and False simultaneously"
        
        result = await engine.reason(
            task=task,
            context={},
            max_h_iterations=5,
            max_l_cycles=3,
            convergence_threshold=0.8
        )
        
        # Property: Should not achieve high confidence on impossible tasks
        confidence = result["metadata"]["confidence_score"]
        assert confidence < 0.6, f"Should have low confidence {confidence} for impossible task"
        
        # Property: Should not falsely claim convergence
        convergence = result["metadata"]["convergence_achieved"]
        if convergence:
            # If it claims convergence, solution should acknowledge the impossibility
            solution_str = str(result["solution"]).lower()
            contradiction_indicators = ["impossible", "cannot", "contradiction", "error", "invalid"]
            has_indicator = any(indicator in solution_str for indicator in contradiction_indicators)
            assert has_indicator, "Converged solution should acknowledge impossibility"


class TestMCPToolsIntegration:
    """Test MCP tools with realistic end-to-end workflows."""
    
    # Use the isolated server fixture for all MCP tests
    
    @pytest.mark.asyncio
    async def test_hierarchical_reason_tool_full_workflow(self, isolated_server: HRMServer) -> None:
        """Test the full workflow of hierarchical reasoning tool."""
        from src.tools import register_tools
        
        # Register tools
        register_tools(isolated_server.mcp, isolated_server)
        
        # Get the tool function
        tools_list = await isolated_server.mcp.list_tools()
        tools_dict = {tool.name: tool for tool in tools_list}
        assert "hierarchical_reason" in tools_dict
        
        # Access the tool function through the server's registered tools
        from src.tools import register_tools
        
        # We need to access the actual function, not just the tool metadata
        # Get the registered tool function directly from the MCP server
        hierarchical_reason_func = None
        for tool_name, tool_info in isolated_server.mcp._tool_manager._tools.items():
            if tool_name == "hierarchical_reason":
                # The FastMCP tool has a 'fn' attribute that contains the actual function
                hierarchical_reason_func = tool_info.fn
                break
        
        assert hierarchical_reason_func is not None, "hierarchical_reason tool handler not found"
        
        # Test with a realistic coding task
        result = await hierarchical_reason_func(
            task="Implement a binary search tree with insert, search, and delete operations",
            context={
                "language": "python",
                "requirements": ["maintain BST properties", "handle duplicates", "efficient operations"]
            },
            max_h_iterations=4,
            max_l_cycles_per_h=5,
            convergence_threshold=0.75
        )
        
        # Property: Should not error out
        assert "error" not in result or result["error"] is None
        
        # Property: Should produce a solution
        assert "solution" in result
        assert result["solution"] is not None
        
        # Property: Should have session tracking
        assert "session_id" in result
        
        # Property: Should have metadata about the reasoning process
        assert "metadata" in result
        metadata = result["metadata"]
        assert not metadata.get("error", False), f"Should not have error in metadata: {metadata}"
    
    @pytest.mark.asyncio
    async def test_task_decomposition_creates_actionable_subtasks(self, isolated_server: HRMServer) -> None:
        """Test that task decomposition creates actually actionable subtasks."""
        from src.tools import register_tools
        
        register_tools(isolated_server.mcp, isolated_server)
        tools_list = await isolated_server.mcp.list_tools()
        tools_dict = {tool.name: tool for tool in tools_list}
        assert "decompose_task" in tools_dict
        
        # Get the actual tool function
        decompose_task_func = None
        for tool_name, tool_info in isolated_server.mcp._tool_manager._tools.items():
            if tool_name == "decompose_task":
                # The FastMCP tool has a 'fn' attribute that contains the actual function
                decompose_task_func = tool_info.fn
                break
        
        assert decompose_task_func is not None, "decompose_task tool handler not found"
        
        result = await decompose_task_func(
            task="Build a REST API for a book library management system",
            max_depth=3
        )
        
        # Property: Should not error
        assert "error" not in result or result["error"] is None
        
        # Property: Should create multiple subtasks
        subtasks = result["subtasks"]
        assert len(subtasks) >= 2, "Complex task should have multiple subtasks"
        
        # Property: Each subtask should be actionable (contain action verbs)
        action_verbs = {"create", "implement", "design", "build", "add", "define", "setup", "configure"}
        for subtask in subtasks:
            description = subtask["description"].lower()
            has_action = any(verb in description for verb in action_verbs)
            assert has_action, f"Subtask '{subtask['description']}' should contain action verb"
            
        # Property: Estimated complexity should be reasonable
        complexity = result["estimated_complexity"]
        assert 0.0 <= complexity <= 1.0, f"Complexity {complexity} should be normalized"


class TestSessionLifecycleProperties:
    """Test properties that must hold throughout session lifecycle."""
    
    @pytest.mark.asyncio
    async def test_session_state_consistency(self, isolated_server: HRMServer) -> None:
        """Verify session state remains consistent throughout operations."""
        server = isolated_server
        
        # Property: Initially no active sessions
        assert len(server.active_sessions) == 0
        
        # Create session
        session_id = await server.create_session()
        
        # Property: Session should be trackable
        assert session_id in server.active_sessions
        session = server.active_sessions[session_id]
        assert session.status == SessionStatus.ACTIVE
        
        # Property: Session should be retrievable
        retrieved_session = await server.get_session(session_id)
        assert retrieved_session is not None
        assert retrieved_session.session_id == session_id
        
        # Complete session
        test_result = {"test": "solution"}
        await server.complete_session(session_id, test_result)
        
        # Property: Completed session should be removed from active sessions
        assert session_id not in server.active_sessions, "Completed sessions should be removed from active sessions"
        
        # Property: But should be retrievable via get_session (from database)
        final_session = await server.get_session(session_id)
        assert final_session is not None
        assert final_session.status == SessionStatus.COMPLETED
        assert final_session.final_solution == test_result
    
    @pytest.mark.asyncio
    async def test_concurrent_session_limits_enforced(self, isolated_server: HRMServer) -> None:
        """Test that concurrent session limits are actually enforced."""
        server = isolated_server
        max_sessions = server.config["server"]["max_concurrent_sessions"]
        
        # Create maximum allowed sessions
        session_ids = []
        for _ in range(max_sessions):
            session_id = await server.create_session()
            session_ids.append(session_id)
        
        # Property: Should have created exactly max sessions
        assert len(server.active_sessions) == max_sessions
        
        # Property: Next session creation should fail
        with pytest.raises(RuntimeError, match="Maximum concurrent sessions reached"):
            await server.create_session()
        
        # Property: After completing a session, should be able to create new one
        await server.complete_session(session_ids[0], {"completed": True})
        
        # This should now work
        new_session_id = await server.create_session()
        assert new_session_id is not None
        # Should be back at max sessions: we removed one by completion, then added a new one
        assert len(server.active_sessions) == max_sessions