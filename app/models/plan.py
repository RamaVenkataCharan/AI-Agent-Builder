from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class EvaluationVerdictType(str, Enum):
    PASS = "pass"
    RETRY = "retry"
    REPLAN = "replan"
    FAIL = "fail"


class TaskStep(BaseModel):
    id: str = Field(description="Unique task identifier (e.g. task_1)")
    order: int = Field(description="Execution sequence order (1-indexed)")
    title: str = Field(description="Short human-readable task title")
    description: str = Field(description="Detailed instructions of what to accomplish")
    dependencies: List[str] = Field(default_factory=list, description="IDs of prerequisite steps that must complete first")
    suggested_tool: Optional[str] = Field(default=None, description="Recommended tool name")
    tool_input_hint: Optional[Dict[str, Any]] = Field(default=None, description="Suggested tool parameters")
    expected_outcome: str = Field(description="Explicit, verifiable acceptance criteria for the Evaluator")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current execution state")
    retry_count: int = Field(default=0, description="Number of retries attempted")
    output: Optional[str] = Field(default=None, description="Intermediate or final task output")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")


class Plan(BaseModel):
    goal: str = Field(description="Original user goal")
    summary: str = Field(description="High-level plan overview and execution strategy")
    steps: List[TaskStep] = Field(default_factory=list, description="Ordered task steps with dependencies")
    version: int = Field(default=1, description="Plan version incremented on replans")


class EvaluationVerdict(BaseModel):
    verdict: EvaluationVerdictType = Field(description="Verdict: pass, retry, replan, fail")
    score: float = Field(default=1.0, ge=0.0, le=1.0, description="Quality/completion score (0.0 to 1.0)")
    reason: str = Field(description="One-line crisp rationale for this verdict")
    feedback: str = Field(description="Detailed analysis of whether the step strictly satisfied the expected acceptance criteria")
    suggested_action: Optional[str] = Field(default=None, description="Action recommendation (e.g. retry with parameter adjustment, replan, proceed)")
