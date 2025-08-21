from typing import Any, Dict, TYPE_CHECKING
from uuid import uuid4

from .models import TaskInput, ReasoningResult
from .reasoning_engine import ReasoningEngine

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from .hrm_mcp_server import HRMServer


def register_tools(mcp: "FastMCP", server: "HRMServer") -> None:
    @mcp.tool()
    async def hierarchical_reason(
        task: str,
        context: Dict[str, Any] | None = None,
        max_h_iterations: int = 10,
        max_l_cycles_per_h: int = 6,
        convergence_threshold: float = 0.85,
        verbosity: str = "normal"
    ) -> Dict[str, Any]:
        """
        Perform hierarchical reasoning on a complex task using HRM-inspired approach.
        
        Args:
            task: The main task to solve
            context: Additional context including existing code, constraints, etc.
            max_h_iterations: Maximum H-module iterations
            max_l_cycles_per_h: Maximum L-module cycles per H-iteration
            convergence_threshold: Global convergence threshold
            verbosity: Output verbosity level
        
        Returns:
            Structured reasoning result with solution and trace
        """
        try:
            context = context or {}
            
            input_data = TaskInput(
                task=task,
                context=context,
                max_h_iterations=max_h_iterations,
                max_l_cycles_per_h=max_l_cycles_per_h,
                convergence_threshold=convergence_threshold
            )
            
            session_id = await server.create_session()
            
            engine = ReasoningEngine()
            result = await engine.reason(
                task=input_data.task,
                context=input_data.context,
                max_h_iterations=input_data.max_h_iterations,
                max_l_cycles=input_data.max_l_cycles_per_h,
                convergence_threshold=input_data.convergence_threshold
            )
            
            await server.complete_session(session_id, result)
            
            return {
                "session_id": str(session_id),
                "solution": result["solution"],
                "reasoning_trace": result["reasoning_trace"],
                "metadata": result["metadata"]
            }
            
        except Exception as e:
            return {
                "error": f"Reasoning failed: {str(e)}",
                "solution": None,
                "reasoning_trace": {},
                "metadata": {"error": True}
            }
    
    @mcp.tool()
    async def decompose_task(
        task: str,
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Decompose a complex task into hierarchical subtasks.
        
        Args:
            task: The task to decompose
            max_depth: Maximum decomposition depth
        
        Returns:
            Hierarchical task decomposition tree
        """
        try:
            engine = ReasoningEngine()
            engine.h_module.initialize_problem(task, {})
            
            goals = engine.h_module.state.pending_subgoals
            
            decomposition = {
                "original_task": task,
                "subtasks": [
                    {
                        "id": goal.id,
                        "description": goal.description,
                        "completed": goal.completed,
                        "confidence": goal.confidence
                    }
                    for goal in goals
                ],
                "total_subtasks": len(goals),
                "estimated_complexity": min(len(goals) / 3, 1.0)
            }
            
            return decomposition
            
        except Exception as e:
            return {
                "error": f"Decomposition failed: {str(e)}",
                "subtasks": [],
                "total_subtasks": 0
            }
    
    @mcp.tool()
    async def refine_solution(
        original_solution: Dict[str, Any],
        refinement_goals: list[str],
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Refine an existing solution with specific optimization goals.
        
        Args:
            original_solution: The solution to refine
            refinement_goals: List of specific refinement objectives
            max_iterations: Maximum refinement iterations
        
        Returns:
            Refined solution with improvement trace
        """
        try:
            task = f"Refine solution with goals: {', '.join(refinement_goals)}"
            context = {
                "original_solution": original_solution,
                "refinement_goals": refinement_goals
            }
            
            engine = ReasoningEngine()
            result = await engine.reason(
                task=task,
                context=context,
                max_h_iterations=max_iterations,
                max_l_cycles=4,
                convergence_threshold=0.80
            )
            
            return {
                "refined_solution": result["solution"],
                "improvements": refinement_goals,
                "refinement_trace": result["reasoning_trace"],
                "confidence_improvement": result["metadata"]["confidence_score"]
            }
            
        except Exception as e:
            return {
                "error": f"Refinement failed: {str(e)}",
                "refined_solution": original_solution,
                "improvements": []
            }
    
    @mcp.tool()
    async def analyze_reasoning_trace(
        session_id: str
    ) -> Dict[str, Any]:
        """
        Analyze the reasoning trace from a completed session.
        
        Args:
            session_id: ID of the session to analyze
        
        Returns:
            Analysis of reasoning patterns and bottlenecks
        """
        try:
            from uuid import UUID
            
            session_uuid = UUID(session_id)
            session = await server.get_session(session_uuid)
            
            if not session or not session.final_solution:
                return {
                    "error": "Session not found or incomplete",
                    "analysis": {}
                }
            
            trace = session.final_solution.get("reasoning_trace", {})
            metadata = session.final_solution.get("metadata", {})
            
            analysis = {
                "session_summary": {
                    "total_iterations": metadata.get("total_iterations", 0),
                    "computation_time": metadata.get("computation_time", 0.0),
                    "convergence_achieved": metadata.get("convergence_achieved", False),
                    "final_confidence": metadata.get("confidence_score", 0.0)
                },
                "performance_metrics": {
                    "iterations_per_second": (
                        metadata.get("total_iterations", 0) / 
                        max(metadata.get("computation_time", 1.0), 0.1)
                    ),
                    "convergence_efficiency": (
                        1.0 if metadata.get("convergence_achieved") else 0.5
                    )
                },
                "bottleneck_analysis": {
                    "slow_convergence": metadata.get("total_iterations", 0) > 8,
                    "low_confidence": metadata.get("confidence_score", 0.0) < 0.7,
                    "recommendations": []
                }
            }
            
            # Add recommendations based on analysis
            if analysis["bottleneck_analysis"]["slow_convergence"]:
                analysis["bottleneck_analysis"]["recommendations"].append(
                    "Consider breaking down the task into smaller subtasks"
                )
            
            if analysis["bottleneck_analysis"]["low_confidence"]:
                analysis["bottleneck_analysis"]["recommendations"].append(
                    "Task may need more context or clearer constraints"
                )
            
            return analysis
            
        except Exception as e:
            return {
                "error": f"Analysis failed: {str(e)}",
                "analysis": {}
            }