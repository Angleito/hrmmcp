import pytest
from src.convergence import ConvergenceDetector
from src.models import HModuleState, Goal, Decision, DecisionType
from src.reasoning_engine import ReasoningEngine


class TestConvergenceBusinessLogic:
    """Test convergence detection logic that actually matters for reasoning quality."""
    
    def test_local_convergence_requires_actual_stability(self) -> None:
        """Test that convergence requires real stability, not just meeting minimum data requirements."""
        # Oscillating values should not converge even with enough data points
        oscillating = [0.5, 0.8, 0.5, 0.8, 0.5, 0.8, 0.5]
        assert not ConvergenceDetector.check_local_convergence(oscillating, threshold=0.95)
        
        # Trending upward should not converge until actually stable
        trending = [0.5, 0.6, 0.7, 0.8, 0.9]
        assert not ConvergenceDetector.check_local_convergence(trending, threshold=0.95)
        
        # Only truly stable sequences should converge
        stable = [0.82, 0.83, 0.82, 0.83, 0.82]
        assert ConvergenceDetector.check_local_convergence(stable, threshold=0.95)
    
    def test_global_convergence_enforces_meaningful_completion(self) -> None:
        """Test that global convergence requires meaningful task completion."""
        # High confidence alone should not be enough
        high_confidence_incomplete = HModuleState(
            problem_representation={"task": "complex problem"},
            completed_subgoals=[],
            pending_subgoals=[Goal(description="unsolved subtask")],
            overall_confidence=0.95
        )
        assert not ConvergenceDetector.check_global_convergence(high_confidence_incomplete)
        
        # Completed goals with low confidence should not converge
        low_confidence_complete = HModuleState(
            problem_representation={"task": "complex problem"},
            completed_subgoals=[Goal(description="solved", completed=True)],
            pending_subgoals=[],
            overall_confidence=0.5  # Below typical threshold
        )
        assert not ConvergenceDetector.check_global_convergence(low_confidence_complete, confidence_threshold=0.85)
        
        # Both completion AND confidence required for true convergence
        meaningful_convergence = HModuleState(
            problem_representation={"task": "complex problem"},
            completed_subgoals=[
                Goal(description="analyzed requirements", completed=True),
                Goal(description="designed solution", completed=True),
                Goal(description="implemented code", completed=True)
            ],
            pending_subgoals=[],
            overall_confidence=0.88
        )
        assert ConvergenceDetector.check_global_convergence(meaningful_convergence)
    
    def test_progress_calculation_reflects_actual_progress(self) -> None:
        """Test that progress score accurately reflects reasoning advancement."""
        # No progress scenario
        no_progress = HModuleState(
            problem_representation={},
            completed_subgoals=[],
            pending_subgoals=[Goal(description="task1"), Goal(description="task2")],
            overall_confidence=0.3
        )
        progress = ConvergenceDetector.calculate_progress_score(no_progress)
        assert progress < 0.4, f"No completed tasks should have low progress, got {progress}"
        
        # Partial progress scenario
        partial_progress = HModuleState(
            problem_representation={},
            completed_subgoals=[Goal(description="completed", completed=True)],
            pending_subgoals=[Goal(description="pending")],
            overall_confidence=0.7
        )
        progress = ConvergenceDetector.calculate_progress_score(partial_progress)
        assert 0.5 <= progress <= 0.8, f"Half-completed should be mid-range progress, got {progress}"
        
        # Full progress scenario
        full_progress = HModuleState(
            problem_representation={},
            completed_subgoals=[Goal(description="task1", completed=True), 
                              Goal(description="task2", completed=True)],
            pending_subgoals=[],
            overall_confidence=0.9
        )
        progress = ConvergenceDetector.calculate_progress_score(full_progress)
        assert progress > 0.9, f"Fully completed should have high progress, got {progress}"
    
    def test_early_termination_prevents_infinite_reasoning(self) -> None:
        """Test that early termination logic prevents runaway reasoning processes."""
        # Create state with consistently poor decisions
        poor_decisions = [
            Decision(type=DecisionType.ALGORITHMIC, rationale="guess 1", confidence=0.2),
            Decision(type=DecisionType.ALGORITHMIC, rationale="guess 2", confidence=0.1),
            Decision(type=DecisionType.ALGORITHMIC, rationale="guess 3", confidence=0.25)
        ]
        
        struggling_state = HModuleState(
            problem_representation={"task": "impossible problem"},
            strategic_decisions=poor_decisions,
            pending_subgoals=[Goal(description="unsolvable")],
            overall_confidence=0.1,
            iteration=5
        )
        
        # Should terminate early due to low confidence decisions
        should_terminate = ConvergenceDetector.should_terminate_early(
            struggling_state, max_iterations=10, no_progress_limit=3
        )
        assert should_terminate, "Should terminate when decisions consistently have low confidence"
        
        # Productive reasoning should continue
        good_decisions = [
            Decision(type=DecisionType.ALGORITHMIC, rationale="solid approach", confidence=0.8),
            Decision(type=DecisionType.ALGORITHMIC, rationale="refinement", confidence=0.85)
        ]
        
        productive_state = HModuleState(
            problem_representation={"task": "solvable problem"},
            strategic_decisions=good_decisions,
            pending_subgoals=[Goal(description="in progress")],
            overall_confidence=0.7,
            iteration=3
        )
        
        should_continue = ConvergenceDetector.should_terminate_early(
            productive_state, max_iterations=10, no_progress_limit=3
        )
        assert not should_continue, "Should continue when making good progress"


class TestReasoningEngineBusinessLogic:
    """Test that reasoning engine produces logically sound results."""
    
    @pytest.mark.asyncio
    async def test_reasoning_quality_degrades_with_impossible_tasks(self) -> None:
        """Test that reasoning engine appropriately handles impossible/contradictory tasks."""
        engine = ReasoningEngine()
        
        # Test with an impossible task
        impossible_result = await engine.reason(
            task="Create a function that both sorts and reverses a list simultaneously while maintaining original order",
            context={},
            max_h_iterations=3,
            max_l_cycles=3
        )
        
        # Should have low confidence for impossible task
        impossible_confidence = impossible_result["metadata"]["confidence_score"]
        assert impossible_confidence < 0.6, f"Should have low confidence for impossible task, got {impossible_confidence}"
        
        # Test with a well-defined possible task
        possible_result = await engine.reason(
            task="Implement binary search algorithm for a sorted array",
            context={"language": "python", "requirements": ["O(log n) time complexity"]},
            max_h_iterations=3,
            max_l_cycles=3
        )
        
        possible_confidence = possible_result["metadata"]["confidence_score"]
        
        # Should have higher confidence for well-defined task
        assert possible_confidence > impossible_confidence, \
            f"Well-defined task confidence ({possible_confidence}) should exceed impossible task confidence ({impossible_confidence})"
    
    @pytest.mark.asyncio
    async def test_reasoning_incorporates_context_meaningfully(self) -> None:
        """Test that context actually influences reasoning outcomes."""
        engine = ReasoningEngine()
        
        base_task = "Implement error handling for user input validation"
        
        # Test with minimal context
        minimal_context_result = await engine.reason(
            task=base_task,
            context={},
            max_h_iterations=2,
            max_l_cycles=2
        )
        
        # Test with rich context
        rich_context_result = await engine.reason(
            task=base_task,
            context={
                "existing_validation": "regex-based email validation",
                "error_requirements": ["user-friendly messages", "localization support"],
                "constraints": ["must not expose internal details", "log security events"],
                "target_framework": "Flask web application"
            },
            max_h_iterations=2,
            max_l_cycles=2
        )
        
        # Rich context should lead to more confident/detailed reasoning
        minimal_confidence = minimal_context_result["metadata"]["confidence_score"]
        rich_confidence = rich_context_result["metadata"]["confidence_score"]
        
        # Either rich context improves confidence, or produces more detailed trace
        rich_trace_length = len(str(rich_context_result["reasoning_trace"]))
        minimal_trace_length = len(str(minimal_context_result["reasoning_trace"]))
        
        context_improves_reasoning = (rich_confidence > minimal_confidence or 
                                    rich_trace_length > minimal_trace_length)
        
        assert context_improves_reasoning, \
            f"Rich context should improve reasoning: confidence {rich_confidence} vs {minimal_confidence}, trace length {rich_trace_length} vs {minimal_trace_length}"
    
    @pytest.mark.asyncio
    async def test_iteration_limits_prevent_infinite_reasoning(self) -> None:
        """Test that iteration limits are actually enforced."""
        engine = ReasoningEngine()
        
        # Test with very low limits
        strict_limit_result = await engine.reason(
            task="Design a comprehensive web application architecture",
            context={},
            max_h_iterations=1,  # Very restrictive
            max_l_cycles=1
        )
        
        iterations = strict_limit_result["metadata"]["total_iterations"]
        assert iterations <= 1, f"Should respect H-iteration limit of 1, got {iterations}"
        
        # Should still produce some result even with tight limits
        assert "solution" in strict_limit_result
        assert strict_limit_result["solution"] is not None