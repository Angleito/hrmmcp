import pytest
from src.convergence import ConvergenceDetector
from src.models import HModuleState, Goal
from src.reasoning_engine import ReasoningEngine


class TestConvergenceDetector:
    def test_local_convergence_insufficient_data(self) -> None:
        history = [0.5, 0.6]
        assert not ConvergenceDetector.check_local_convergence(history)
    
    def test_local_convergence_achieved(self) -> None:
        history = [0.85, 0.86, 0.85, 0.85]
        assert ConvergenceDetector.check_local_convergence(history, threshold=0.95)
    
    def test_global_convergence_no_completed_goals(self) -> None:
        state = HModuleState(
            problem_representation={},
            completed_subgoals=[],
            pending_subgoals=[Goal(description="test")],
            overall_confidence=0.9
        )
        assert not ConvergenceDetector.check_global_convergence(state)
    
    def test_global_convergence_achieved(self) -> None:
        state = HModuleState(
            problem_representation={},
            completed_subgoals=[Goal(description="test", completed=True)],
            pending_subgoals=[],
            overall_confidence=0.9
        )
        assert ConvergenceDetector.check_global_convergence(state)


class TestReasoningEngine:
    @pytest.mark.asyncio
    async def test_reasoning_basic_task(self) -> None:
        engine = ReasoningEngine()
        result = await engine.reason(
            task="implement a simple calculator",
            context={},
            max_h_iterations=3,
            max_l_cycles=3
        )
        
        assert "solution" in result
        assert "reasoning_trace" in result
        assert "metadata" in result
        assert result["metadata"]["confidence_score"] > 0.0
    
    @pytest.mark.asyncio
    async def test_reasoning_with_context(self) -> None:
        engine = ReasoningEngine()
        context = {
            "existing_code": "def add(a, b): return a + b",
            "constraints": ["must handle errors", "must be type safe"]
        }
        
        result = await engine.reason(
            task="extend calculator with multiplication",
            context=context,
            max_h_iterations=2
        )
        
        assert result["metadata"]["convergence_achieved"] is True or False
        assert result["metadata"]["total_iterations"] <= 2