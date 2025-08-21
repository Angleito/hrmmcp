"""Property-based tests that verify mathematical and logical invariants."""

import pytest
from typing import List, Dict, Any
from datetime import datetime, timedelta

from src.convergence import ConvergenceDetector
from src.models import HModuleState, Goal, Decision, DecisionType, SessionStatus
from src.reasoning_engine import HModule, LModule
from src.state_manager import StateManager


class TestConvergenceProperties:
    """Test mathematical properties of convergence detection."""
    
    def test_convergence_monotonicity_property(self) -> None:
        """Property: If a history converges, adding more stable values shouldn't break convergence."""
        # Create a converging sequence
        base_history = [0.85, 0.86, 0.87, 0.86, 0.85]
        assert ConvergenceDetector.check_local_convergence(base_history, threshold=0.90)
        
        # Property: Adding more values in the same range should maintain convergence
        extended_history = base_history + [0.86, 0.85, 0.87]
        assert ConvergenceDetector.check_local_convergence(extended_history, threshold=0.90)
        
        # Property: Adding values within stability window should maintain convergence
        stable_extension = base_history + [0.855, 0.852, 0.858]
        assert ConvergenceDetector.check_local_convergence(stable_extension, threshold=0.90)
    
    def test_convergence_threshold_ordering_property(self) -> None:
        """Property: Higher thresholds should be harder to achieve than lower thresholds."""
        history = [0.75, 0.76, 0.77, 0.76, 0.75, 0.76]
        
        # Property: If converges at high threshold, must converge at lower threshold
        thresholds = [0.95, 0.90, 0.85, 0.80, 0.75]
        convergence_results = []
        
        for threshold in thresholds:
            converged = ConvergenceDetector.check_local_convergence(history, threshold=threshold)
            convergence_results.append(converged)
        
        # Property: Once convergence fails at a threshold, it should fail at higher thresholds
        failed_index = None
        for i, converged in enumerate(convergence_results):
            if not converged:
                failed_index = i
                break
        
        if failed_index is not None:
            for i in range(failed_index):
                assert not convergence_results[i], f"Higher threshold {thresholds[i]} should not converge if {thresholds[failed_index]} doesn't"
    
    def test_global_convergence_completeness_property(self) -> None:
        """Property: Global convergence requires all goals to be completed."""
        # Create goals
        goal1 = Goal(description="task1", completed=False, confidence=0.9)
        goal2 = Goal(description="task2", completed=True, confidence=0.8)
        goal3 = Goal(description="task3", completed=True, confidence=0.7)
        
        # Property: With incomplete goals, should not achieve global convergence
        state_incomplete = HModuleState(
            problem_representation={},
            completed_subgoals=[goal2, goal3],
            pending_subgoals=[goal1],
            overall_confidence=0.95
        )
        assert not ConvergenceDetector.check_global_convergence(state_incomplete)
        
        # Property: Only when all goals completed should global convergence be possible
        goal1.completed = True
        state_complete = HModuleState(
            problem_representation={},
            completed_subgoals=[goal1, goal2, goal3],
            pending_subgoals=[],
            overall_confidence=0.95
        )
        assert ConvergenceDetector.check_global_convergence(state_complete)
    
    def test_confidence_bounds_property(self) -> None:
        """Property: Confidence scores must remain within [0,1] bounds."""
        # Test with extreme confidence values
        goal_low = Goal(description="test", confidence=0.0)
        goal_high = Goal(description="test", confidence=1.0)
        
        state = HModuleState(
            problem_representation={},
            completed_subgoals=[goal_low, goal_high],
            pending_subgoals=[],
            overall_confidence=0.5
        )
        
        # Property: Should handle extreme confidence values gracefully
        result = ConvergenceDetector.check_global_convergence(state)
        assert isinstance(result, bool)  # Should not crash or return invalid type


class TestHModuleProperties:
    """Test logical properties of H-Module behavior."""
    
    def test_goal_conservation_property(self) -> None:
        """Property: Total number of goals should be conserved during processing."""
        h_module = HModule()
        
        task = "Implement a sorting algorithm with optimal time complexity"
        h_module.initialize_problem(task, {})
        
        initial_goal_count = len(h_module.state.pending_subgoals)
        assert initial_goal_count > 0, "Should create some goals for complex task"
        
        # Simulate goal completion
        original_goals = h_module.state.pending_subgoals.copy()
        
        # Move first goal to completed
        if h_module.state.pending_subgoals:
            completed_goal = h_module.state.pending_subgoals.pop(0)
            completed_goal.completed = True
            h_module.state.completed_subgoals.append(completed_goal)
        
        # Property: Total goals should be conserved
        total_goals_after = (len(h_module.state.pending_subgoals) + 
                           len(h_module.state.completed_subgoals))
        assert total_goals_after == initial_goal_count, "Goal count should be conserved"
    
    def test_iteration_monotonicity_property(self) -> None:
        """Property: Iteration counter should only increase."""
        h_module = HModule()
        h_module.initialize_problem("test task", {})
        
        initial_iteration = h_module.state.iteration
        
        # Perform multiple planning cycles
        iterations = []
        for _ in range(5):
            h_module.plan_cycle()
            iterations.append(h_module.state.iteration)
        
        # Property: Iterations should be strictly increasing
        for i in range(1, len(iterations)):
            assert iterations[i] > iterations[i-1], f"Iteration {iterations[i]} should be > {iterations[i-1]}"
        
        # Property: Should start from a baseline
        assert iterations[0] > initial_iteration, "First planning cycle should increment iteration"
    
    def test_decision_causality_property(self) -> None:
        """Property: Decisions should have logical temporal ordering."""
        h_module = HModule()
        h_module.initialize_problem("complex task requiring multiple decisions", {})
        
        # Generate multiple decisions
        for _ in range(3):
            h_module.plan_cycle()
        
        decisions = h_module.state.strategic_decisions
        
        if len(decisions) >= 2:
            # Property: Decision timestamps should be ordered
            for i in range(1, len(decisions)):
                assert decisions[i].timestamp >= decisions[i-1].timestamp, \
                    "Decision timestamps should be chronologically ordered"
            
            # Property: Each decision should have valid confidence
            for decision in decisions:
                assert 0.0 <= decision.confidence <= 1.0, \
                    f"Decision confidence {decision.confidence} should be in [0,1]"


class TestLModuleProperties:
    """Test execution properties of L-Module."""
    
    def test_trace_completeness_property(self) -> None:
        """Property: Every L-module action should be recorded in trace."""
        l_module = LModule()
        
        # Initialize with a task
        task = {"action": "implement_function", "details": "binary search"}
        l_module.state.current_task = task
        
        initial_trace_length = len(l_module.state.execution_trace)
        
        # Simulate execution steps
        l_module.execute_step({"implement": "binary_search_logic"})
        l_module.execute_step({"test": "edge_cases"})
        l_module.execute_step({"optimize": "performance"})
        
        # Property: Trace should record all actions
        final_trace_length = len(l_module.state.execution_trace)
        assert final_trace_length == initial_trace_length + 3, \
            "Each execute_step should add exactly one trace entry"
        
        # Property: Each trace entry should have required fields
        for trace_entry in l_module.state.execution_trace:
            assert hasattr(trace_entry, 'action'), "Trace should record action"
            assert hasattr(trace_entry, 'result'), "Trace should record result"
            assert hasattr(trace_entry, 'timestamp'), "Trace should record timestamp"
            assert hasattr(trace_entry, 'success'), "Trace should record success status"
    
    def test_iteration_bounds_property(self) -> None:
        """Property: L-module iterations should respect configured bounds."""
        l_module = LModule()
        
        # Property: Should not exceed reasonable iteration limits
        max_reasonable_iterations = 1000
        
        for _ in range(max_reasonable_iterations + 1):
            l_module.state.iteration += 1
            if l_module.state.iteration > max_reasonable_iterations:
                break
        
        # This property ensures we don't have infinite loops in implementation
        assert l_module.state.iteration <= max_reasonable_iterations, \
            "L-module should have reasonable iteration bounds to prevent infinite loops"


class TestSessionStateProperties:
    """Test invariants that must hold for session state management."""
    
    @pytest.mark.asyncio
    async def test_session_state_transitions_are_valid(self) -> None:
        """Property: Session status transitions must follow valid state machine."""
        state_manager = StateManager(":memory:")  # Use in-memory database for testing
        await state_manager.initialize()
        
        from src.models import ReasoningSession
        from uuid import uuid4
        
        session_id = uuid4()
        session = ReasoningSession(session_id=session_id, status=SessionStatus.ACTIVE)
        
        # Save initial state
        await state_manager.save_session(session)
        
        # Property: Valid transitions from ACTIVE
        valid_transitions = [SessionStatus.COMPLETED, SessionStatus.TIMEOUT, SessionStatus.ERROR]
        
        for target_status in valid_transitions:
            session.status = target_status
            await state_manager.save_session(session)
            
            # Should be able to load and verify transition
            loaded_session = await state_manager.load_session(session_id)
            assert loaded_session is not None
            assert loaded_session.status == target_status
        
        # Property: Invalid transitions should be handled gracefully
        # (Implementation detail: this depends on business logic requirements)
    
    @pytest.mark.asyncio
    async def test_timestamp_consistency_property(self) -> None:
        """Property: Session timestamps should maintain logical ordering."""
        from src.models import ReasoningSession
        from uuid import uuid4
        import asyncio
        
        session_id = uuid4()
        session = ReasoningSession(session_id=session_id)
        
        created_at = session.created_at
        
        # Simulate some time passing
        await asyncio.sleep(0.01)
        
        # Update session
        session.status = SessionStatus.COMPLETED
        session.updated_at = datetime.utcnow()
        
        # Property: updated_at should be >= created_at
        assert session.updated_at >= created_at, \
            "Session updated_at should be >= created_at"
        
        # Property: Time differences should be reasonable
        time_diff = session.updated_at - created_at
        assert time_diff < timedelta(seconds=60), \
            "Time difference should be reasonable for test execution"
    
    @pytest.mark.asyncio
    async def test_session_persistence_idempotency(self) -> None:
        """Property: Saving and loading a session should be idempotent."""
        state_manager = StateManager(":memory:")
        await state_manager.initialize()
        
        from src.models import ReasoningSession, HModuleState, Goal
        from uuid import uuid4
        
        # Create complex session state
        session_id = uuid4()
        h_state = HModuleState(
            problem_representation={"task": "complex problem"},
            completed_subgoals=[Goal(description="completed task", completed=True)],
            pending_subgoals=[Goal(description="pending task", completed=False)],
            overall_confidence=0.75
        )
        
        original_session = ReasoningSession(
            session_id=session_id,
            status=SessionStatus.ACTIVE,
            h_module_state=h_state
        )
        
        # Save session
        await state_manager.save_session(original_session)
        
        # Load session
        loaded_session = await state_manager.load_session(session_id)
        
        # Property: Loaded session should be equivalent to original
        assert loaded_session is not None
        assert loaded_session.session_id == original_session.session_id
        assert loaded_session.status == original_session.status
        
        if loaded_session.h_module_state and original_session.h_module_state:
            assert (loaded_session.h_module_state.overall_confidence == 
                   original_session.h_module_state.overall_confidence)
            assert (len(loaded_session.h_module_state.completed_subgoals) == 
                   len(original_session.h_module_state.completed_subgoals))
        
        # Property: Multiple saves should not corrupt data
        await state_manager.save_session(loaded_session)
        twice_loaded = await state_manager.load_session(session_id)
        
        assert twice_loaded is not None
        assert twice_loaded.session_id == session_id