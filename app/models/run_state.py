from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.plan import EvaluationVerdict, Plan


class RunStatus(str, Enum):
    INITIALIZED = "initialized"
    PLANNING = "planning"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class LogEntry(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    level: str = Field(default="INFO")  # INFO, WARNING, ERROR, SUCCESS
    source: str = Field(description="Component logging the message (Planner, Executor, Evaluator, Tool)")
    message: str


class StepExecutionRecord(BaseModel):
    step_id: str
    step_order: int
    step_title: str
    tool_used: Optional[str] = None
    tool_selection_reasoning: Optional[str] = Field(default=None, description="Explicit rationale for why this tool was chosen")
    tool_inputs: Optional[Dict[str, Any]] = None
    tool_output: Optional[str] = None
    tool_status: str = "success"  # success, error
    evaluation: Optional[EvaluationVerdict] = None
    memory_reads: List[str] = Field(default_factory=list, description="IDs of memory records retrieved to execute this step")
    memory_writes: List[str] = Field(default_factory=list, description="IDs of memory records stored from this step output")
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None


class AgentRun(BaseModel):
    run_id: str
    goal: str
    status: RunStatus = RunStatus.INITIALIZED
    current_iteration: int = 0
    max_iterations: int = 10
    total_tokens_estimated: int = 0
    cost_budget_usd: float = 2.0
    cost_spent_usd: float = 0.0
    plan: Optional[Plan] = None
    step_records: List[StepExecutionRecord] = Field(default_factory=list)
    logs: List[LogEntry] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    final_result: Optional[str] = None
    error_message: Optional[str] = None


class GoalSubmissionRequest(BaseModel):
    goal: str = Field(..., min_length=3, description="Natural language goal to execute")
    llm_provider: Optional[str] = Field(default=None, description="Override default provider (ollama, openai, mock)")
    llm_model: Optional[str] = Field(default=None, description="Override default model name")
    max_iterations: Optional[int] = Field(default=None, description="Override max loop iterations")
    cost_budget_usd: Optional[float] = Field(default=None, description="Cost limit in USD for paid providers")
