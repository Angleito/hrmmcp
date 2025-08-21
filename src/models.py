from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    IMPLEMENTATION = "implementation"
    REFACTORING = "refactoring" 
    DEBUGGING = "debugging"
    OPTIMIZATION = "optimization"


class DecisionType(str, Enum):
    ARCHITECTURAL = "architectural"
    ALGORITHMIC = "algorithmic"
    STRUCTURAL = "structural"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"


class VerbosityLevel(str, Enum):
    MINIMAL = "minimal"
    NORMAL = "normal"
    DETAILED = "detailed"


class Constraint(BaseModel):
    description: str
    hard: bool = True
    satisfied: bool = False


class Goal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    description: str
    completed: bool = False
    confidence: float = 0.0


class Decision(BaseModel):
    type: DecisionType
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HModuleState(BaseModel):
    problem_representation: Dict[str, Any]
    strategic_decisions: List[Decision] = Field(default_factory=list)
    global_context: Dict[str, Any] = Field(default_factory=dict)
    completed_subgoals: List[Goal] = Field(default_factory=list)
    pending_subgoals: List[Goal] = Field(default_factory=list)
    overall_confidence: float = 0.0
    iteration: int = 0


class LModuleTrace(BaseModel):
    action: str
    result: Any
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool


class LModuleState(BaseModel):
    current_task: Dict[str, Any]
    execution_trace: List[LModuleTrace] = Field(default_factory=list)
    local_optimizations: List[Dict[str, Any]] = Field(default_factory=list)
    iteration: int = 0


class ReasoningSession(BaseModel):
    session_id: UUID = Field(default_factory=uuid4)
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    h_module_state: Optional[HModuleState] = None
    l_module_state: Optional[LModuleState] = None
    final_solution: Optional[Dict[str, Any]] = None


class TaskInput(BaseModel):
    task: str
    context: Dict[str, Any] = Field(default_factory=dict)
    max_h_iterations: int = Field(default=10, ge=1, le=50)
    max_l_cycles_per_h: int = Field(default=6, ge=3, le=20)
    convergence_threshold: float = Field(default=0.85, ge=0.5, le=1.0)
    verbosity: VerbosityLevel = VerbosityLevel.NORMAL


class ReasoningResult(BaseModel):
    solution: Dict[str, Any]
    reasoning_trace: Dict[str, Any]
    confidence_score: float = Field(ge=0.0, le=1.0)
    total_iterations: int
    computation_time: float
    convergence_achieved: bool