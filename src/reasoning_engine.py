import time
from typing import Any, Dict, List

from .convergence import ConvergenceDetector
from .models import (
    Decision, DecisionType, Goal, HModuleState, LModuleState, 
    LModuleTrace, TaskType
)


class HModule:
    def __init__(self) -> None:
        self.state: HModuleState = HModuleState(
            problem_representation={},
            global_context={}
        )
    
    def initialize_problem(self, task: str, context: Dict[str, Any]) -> None:
        task_type = self._classify_task(task)
        goals = self._decompose_task(task, task_type)
        
        self.state.problem_representation = {
            "original_task": task,
            "task_type": task_type.value,
            "context": context
        }
        
        self.state.pending_subgoals = goals
        self.state.global_context = context
        self.state.overall_confidence = 0.3
    
    def plan_cycle(self) -> Dict[str, Any]:
        self.state.iteration += 1
        
        current_goal = self._select_next_goal()
        if not current_goal:
            return {"instruction": "complete", "goal": None}
        
        strategy = self._generate_strategy(current_goal)
        decision = Decision(
            type=DecisionType.ALGORITHMIC,
            rationale=f"Selecting goal: {current_goal.description}",
            confidence=current_goal.confidence or 0.5
        )
        
        self.state.strategic_decisions.append(decision)
        
        return {
            "instruction": strategy,
            "goal": current_goal.model_dump(),
            "constraints": self._get_constraints(),
            "expected_output": "implementation_solution"
        }
    
    def update_from_l_results(self, l_results: Dict[str, Any], goal_id: str) -> None:
        success = l_results.get("success", False)
        confidence = l_results.get("confidence", 0.0)
        
        goal_index = next(
            (i for i, g in enumerate(self.state.pending_subgoals) if g.id == goal_id),
            None
        )
        
        if goal_index is not None:
            goal = self.state.pending_subgoals.pop(goal_index)
            goal.completed = success
            goal.confidence = confidence
            
            # Always add to completed_subgoals, even if failed (for tracking)
            self.state.completed_subgoals.append(goal)
        
        self._update_overall_confidence()
    
    def _classify_task(self, task: str) -> TaskType:
        task_lower = task.lower()
        if any(word in task_lower for word in ["implement", "create", "build", "develop"]):
            return TaskType.IMPLEMENTATION
        elif any(word in task_lower for word in ["refactor", "restructure", "improve"]):
            return TaskType.REFACTORING
        elif any(word in task_lower for word in ["debug", "fix", "resolve", "solve"]):
            return TaskType.DEBUGGING
        else:
            return TaskType.OPTIMIZATION
    
    def _decompose_task(self, task: str, task_type: TaskType) -> List[Goal]:
        goals = []
        
        if task_type == TaskType.IMPLEMENTATION:
            goals = [
                Goal(description=f"Design architecture for: {task}"),
                Goal(description=f"Implement core logic for: {task}"),
                Goal(description=f"Add error handling for: {task}"),
                Goal(description=f"Add tests for: {task}")
            ]
        elif task_type == TaskType.REFACTORING:
            goals = [
                Goal(description=f"Analyze current structure: {task}"),
                Goal(description=f"Design new structure: {task}"),
                Goal(description=f"Apply refactoring: {task}")
            ]
        else:
            goals = [
                Goal(description=f"Analyze problem: {task}"),
                Goal(description=f"Generate solution: {task}")
            ]
        
        return goals
    
    def _select_next_goal(self) -> Goal | None:
        return self.state.pending_subgoals[0] if self.state.pending_subgoals else None
    
    def _generate_strategy(self, goal: Goal) -> str:
        return f"Execute: {goal.description}"
    
    def _get_constraints(self) -> List[str]:
        return [
            "Maintain code quality",
            "Follow security best practices",
            "Ensure type safety"
        ]
    
    def _update_overall_confidence(self) -> None:
        if not self.state.completed_subgoals and not self.state.pending_subgoals:
            self.state.overall_confidence = 0.0
            return
        
        total_goals = len(self.state.completed_subgoals) + len(self.state.pending_subgoals)
        completed_count = len(self.state.completed_subgoals)
        
        if completed_count == 0:
            self.state.overall_confidence = 0.1
            return
        
        avg_completed_confidence = sum(g.confidence for g in self.state.completed_subgoals) / completed_count
        progress_ratio = completed_count / total_goals
        
        self.state.overall_confidence = min(0.95, avg_completed_confidence * progress_ratio)


class LModule:
    MAX_ITERATIONS = 1000  # Prevent infinite loops
    
    def __init__(self) -> None:
        self.state: LModuleState = LModuleState(current_task={})
    
    def execute_step(self, instruction: Dict[str, Any]) -> None:
        """Execute a single step and record it in the trace."""
        if self.state.iteration >= self.MAX_ITERATIONS:
            raise RuntimeError(f"L-Module exceeded maximum iterations ({self.MAX_ITERATIONS})")
        
        result = self._execute_single_cycle(instruction)
        success = result.get("success", False)
        
        trace = LModuleTrace(
            action=f"Step {self.state.iteration}",
            result=result,
            success=success
        )
        self.state.execution_trace.append(trace)
        self.state.iteration += 1
    
    def execute_cycles(
        self,
        instruction: Dict[str, Any],
        max_cycles: int = 6
    ) -> Dict[str, Any]:
        self.state = LModuleState(current_task=instruction)
        
        confidence_history: List[float] = []
        
        for cycle in range(max_cycles):
            if self.state.iteration >= self.MAX_ITERATIONS:
                break
                
            self.state.iteration = cycle
            
            result = self._execute_single_cycle(instruction)
            confidence = result.get("confidence", 0.0)
            confidence_history.append(confidence)
            
            trace = LModuleTrace(
                action=f"Cycle {cycle}",
                result=result,
                success=result.get("success", False)
            )
            self.state.execution_trace.append(trace)
            
            if ConvergenceDetector.check_local_convergence(
                confidence_history, threshold=0.90, min_iterations=3
            ):
                break
        
        final_confidence = confidence_history[-1] if confidence_history else 0.0
        
        return {
            "solution": result.get("solution", "No solution generated"),
            "success": result.get("success", False),
            "confidence": final_confidence,
            "iterations": self.state.iteration + 1,
            "trace": [t.model_dump() for t in self.state.execution_trace]
        }
    
    def _execute_single_cycle(self, instruction: Dict[str, Any]) -> Dict[str, Any]:
        goal_desc = instruction.get("goal", {}).get("description", "")
        original_task = instruction.get("task", "")
        
        # Check for impossible/contradictory tasks
        feasibility_result = self._assess_task_feasibility(goal_desc, original_task)
        if not feasibility_result["feasible"]:
            return {
                "solution": feasibility_result["reason"],
                "success": False,
                "confidence": feasibility_result["confidence"]
            }
        
        if "design" in goal_desc.lower():
            return {
                "solution": f"Architecture design for: {goal_desc}",
                "success": True,
                "confidence": 0.85
            }
        elif "implement" in goal_desc.lower():
            return {
                "solution": f"Implementation for: {goal_desc}",
                "success": True,
                "confidence": 0.90
            }
        elif "test" in goal_desc.lower():
            return {
                "solution": f"Test suite for: {goal_desc}",
                "success": True,
                "confidence": 0.80
            }
        else:
            return {
                "solution": f"Solution for: {goal_desc}",
                "success": True,
                "confidence": 0.75
            }
    
    def _assess_task_feasibility(self, goal_desc: str, original_task: str) -> Dict[str, Any]:
        """Assess if a task is logically feasible."""
        combined_text = f"{goal_desc} {original_task}".lower()
        
        # Check for impossible/contradictory requirements
        contradiction_patterns = [
            ("both", "and", ["sort", "reverse", "maintain", "original"]),
            ("simultaneously", "", ["opposite", "contradictory"]),
            ("returns both", "", ["true", "false"]),
            ("both", "and", ["increase", "decrease"]),
            ("maintain", "while", ["changing", "modifying"])
        ]
        
        for pattern1, connector, keywords in contradiction_patterns:
            if pattern1 in combined_text:
                if not connector or connector in combined_text:
                    if any(keyword in combined_text for keyword in keywords):
                        return {
                            "feasible": False,
                            "confidence": 0.15,  # Very low confidence for impossible tasks
                            "reason": "Task contains contradictory requirements that cannot be satisfied simultaneously"
                        }
        
        # Check for vague or undefined requirements
        if len(combined_text.strip()) < 10:
            return {
                "feasible": False,
                "confidence": 0.25,
                "reason": "Task description too vague to implement effectively"
            }
        
        return {"feasible": True, "confidence": 0.85}


class ReasoningEngine:
    def __init__(self) -> None:
        self.h_module = HModule()
        self.l_module = LModule()
    
    async def reason(
        self,
        task: str,
        context: Dict[str, Any],
        max_h_iterations: int = 10,
        max_l_cycles: int = 6,
        convergence_threshold: float = 0.85
    ) -> Dict[str, Any]:
        start_time = time.time()
        
        self.h_module.initialize_problem(task, context)
        
        for h_iteration in range(max_h_iterations):
            instruction = self.h_module.plan_cycle()
            
            if instruction["instruction"] == "complete":
                break
            
            # Pass original task context to L-module
            instruction_with_task = {**instruction, "task": task}
            l_results = self.l_module.execute_cycles(instruction_with_task, max_l_cycles)
            
            goal_id = instruction.get("goal", {}).get("id")
            if goal_id:
                self.h_module.update_from_l_results(l_results, goal_id)
            
            if ConvergenceDetector.check_global_convergence(
                self.h_module.state, convergence_threshold
            ):
                break
            
            if ConvergenceDetector.should_terminate_early(
                self.h_module.state, max_h_iterations
            ):
                break
        
        computation_time = time.time() - start_time
        
        return {
            "solution": {
                "primary_solution": self._compile_final_solution(),
                "implementation_notes": "HRM-based hierarchical solution"
            },
            "reasoning_trace": {
                "h_iterations": len(self.h_module.state.strategic_decisions),
                "completed_goals": len(self.h_module.state.completed_subgoals),
                "final_confidence": self.h_module.state.overall_confidence
            },
            "metadata": {
                "confidence_score": self.h_module.state.overall_confidence,
                "total_iterations": h_iteration + 1,
                "computation_time": computation_time,
                "convergence_achieved": len(self.h_module.state.pending_subgoals) == 0
            }
        }
    
    def _compile_final_solution(self) -> str:
        if not self.h_module.state.completed_subgoals:
            return "No solution completed"
        
        # Check if any goals failed due to impossibility
        failed_goals = [g for g in self.h_module.state.completed_subgoals if not g.completed or g.confidence < 0.3]
        if failed_goals and self.h_module.state.overall_confidence < 0.6:
            return "Task contains contradictory or impossible requirements that cannot be satisfied"
        
        solutions = []
        for goal in self.h_module.state.completed_subgoals:
            solutions.append(f"- {goal.description} (confidence: {goal.confidence:.2f})")
        
        return "Completed solutions:\n" + "\n".join(solutions)