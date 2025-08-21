from typing import List

from .models import Goal, HModuleState


class ConvergenceDetector:
    @staticmethod
    def check_local_convergence(
        results_history: List[float],
        threshold: float = 0.95,
        min_iterations: int = 3,
        stability_window: int = 3
    ) -> bool:
        if len(results_history) < min_iterations:
            return False
        
        recent = results_history[-stability_window:]
        if len(recent) < stability_window:
            return False
        
        avg = sum(recent) / len(recent)
        tolerance = 1 - threshold
        
        return all(abs(score - avg) < tolerance for score in recent)
    
    @staticmethod
    def check_global_convergence(
        h_state: HModuleState,
        confidence_threshold: float = 0.85
    ) -> bool:
        if not h_state.completed_subgoals:
            return False
        
        if h_state.pending_subgoals:
            return False
        
        if h_state.overall_confidence < confidence_threshold:
            return False
        
        return True
    
    @staticmethod
    def calculate_progress_score(h_state: HModuleState) -> float:
        total_goals = len(h_state.completed_subgoals) + len(h_state.pending_subgoals)
        if total_goals == 0:
            return 0.0
        
        completed = len(h_state.completed_subgoals)
        progress_ratio = completed / total_goals
        
        confidence_bonus = h_state.overall_confidence * 0.2
        return min(1.0, progress_ratio + confidence_bonus)
    
    @staticmethod
    def should_terminate_early(
        h_state: HModuleState,
        max_iterations: int,
        no_progress_limit: int = 3
    ) -> bool:
        if h_state.iteration >= max_iterations:
            return True
        
        if len(h_state.strategic_decisions) >= no_progress_limit:
            recent_confidence = [
                d.confidence for d in h_state.strategic_decisions[-no_progress_limit:]
            ]
            avg_confidence = sum(recent_confidence) / len(recent_confidence)
            
            if avg_confidence < 0.3:
                return True
        
        return False