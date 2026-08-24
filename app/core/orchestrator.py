import logging
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional
from app.config import settings
from app.core.evaluator import Evaluator
from app.core.executor import Executor
from app.core.planner import Planner
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider
from app.memory.session_memory import SessionMemory
from app.models.plan import EvaluationVerdictType, TaskStatus
from app.models.run_state import AgentRun, LogEntry, RunStatus
from app.tools.registry import ToolRegistry, default_tool_registry

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Master Orchestrator executing the Plan → Execute → Evaluate → Improve loop
    with strict iteration caps, budget guards, and inspectability.
    """

    def __init__(
        self,
        llm_provider: Optional[BaseLLMProvider] = None,
        tool_registry: Optional[ToolRegistry] = None,
        memory: Optional[SessionMemory] = None,
        event_callback: Optional[Callable[[str, AgentRun], None]] = None,
    ):
        self.llm = llm_provider or get_llm_provider()
        self.tool_registry = tool_registry or default_tool_registry
        self.memory = memory or SessionMemory()
        self.planner = Planner(self.llm, self.tool_registry)
        self.executor = Executor(self.llm, self.tool_registry)
        self.evaluator = Evaluator(self.llm)
        self.event_callback = event_callback

    def _log(self, run: AgentRun, source: str, message: str, level: str = "INFO") -> None:
        entry = LogEntry(source=source, message=message, level=level)
        run.logs.append(entry)
        run.updated_at = datetime.now(timezone.utc).isoformat()
        if self.event_callback:
            self.event_callback("log", run)
        logger.info(f"[{source}] {message}")

    def run(
        self,
        goal: str,
        run_id: Optional[str] = None,
        max_iterations: Optional[int] = None,
        cost_budget_usd: Optional[float] = None,
    ) -> AgentRun:
        """Executes the full agent autonomous loop for the given goal with hard limits."""
        active_run_id = run_id or f"run_{uuid.uuid4().hex[:8]}"
        limit_iterations = max_iterations or settings.MAX_ITERATIONS
        budget_usd = cost_budget_usd or 2.0

        run = AgentRun(
            run_id=active_run_id,
            goal=goal,
            status=RunStatus.INITIALIZED,
            max_iterations=limit_iterations,
            cost_budget_usd=budget_usd,
        )

        self._log(run, "Orchestrator", f"Starting Agent run for goal: '{goal}' (Max Iterations: {limit_iterations})")

        # 1. Planning Stage
        run.status = RunStatus.PLANNING
        self._log(run, "Planner", "Decomposing goal into structured task steps...")
        plan = self.planner.create_plan(goal=goal, memory=self.memory)
        run.plan = plan
        self._log(run, "Planner", f"Created plan (v{plan.version}) with {len(plan.steps)} steps: '{plan.summary}'")

        # 2. Execution & Evaluation Loop
        step_idx = 0
        iteration = 0

        while step_idx < len(run.plan.steps):
            # Check Iteration Cap
            if iteration >= run.max_iterations:
                run.status = RunStatus.FAILED
                run.error_message = f"Hard iteration limit ({run.max_iterations}) breached without completing all steps."
                self._log(run, "Orchestrator", run.error_message, level="ERROR")
                break

            # Check Cost / Budget Cap
            if run.cost_spent_usd >= run.cost_budget_usd:
                run.status = RunStatus.FAILED
                run.error_message = f"Cost budget limit (${run.cost_budget_usd:.2f}) exceeded (Spent: ${run.cost_spent_usd:.2f})."
                self._log(run, "Orchestrator", run.error_message, level="ERROR")
                break

            iteration += 1
            run.current_iteration = iteration
            current_step = run.plan.steps[step_idx]

            run.status = RunStatus.EXECUTING
            current_step.status = TaskStatus.RUNNING
            self._log(
                run,
                "Executor",
                f"Executing Step {current_step.order}/{len(run.plan.steps)}: '{current_step.title}' (Iteration {iteration})"
            )

            # Execute Step via Executor & Tools
            record = self.executor.execute_step(
                step=current_step,
                memory=self.memory,
                goal=goal,
            )

            current_step.output = record.tool_output
            self._log(
                run,
                "Executor",
                f"Step {current_step.order} executed via tool '{record.tool_used}' in {record.duration_seconds}s. Reasoning: {record.tool_selection_reasoning}"
            )

            # 3. Skeptical Evaluation Stage
            run.status = RunStatus.EVALUATING
            self._log(run, "Evaluator", f"Evaluating output against criteria: '{current_step.expected_outcome}'")
            verdict = self.evaluator.evaluate_step(goal=goal, step=current_step, record=record)
            record.evaluation = verdict
            run.step_records.append(record)

            self._log(
                run,
                "Evaluator",
                f"Verdict: {verdict.verdict.value.upper()} | Score: {verdict.score} | Reason: {verdict.reason}",
                level="SUCCESS" if verdict.verdict == EvaluationVerdictType.PASS else "WARNING"
            )

            # 4. Handle Verdict Actions
            if verdict.verdict == EvaluationVerdictType.PASS:
                current_step.status = TaskStatus.COMPLETED
                step_idx += 1  # Advance sequence

            elif verdict.verdict == EvaluationVerdictType.RETRY:
                current_step.retry_count += 1
                if current_step.retry_count <= settings.MAX_STEP_RETRIES:
                    current_step.status = TaskStatus.RETRYING
                    self._log(
                        run,
                        "Evaluator",
                        f"Retrying step '{current_step.title}' (Attempt {current_step.retry_count}/{settings.MAX_STEP_RETRIES}): {verdict.reason}"
                    )
                else:
                    self._log(run, "Evaluator", f"Max retries ({settings.MAX_STEP_RETRIES}) reached for step '{current_step.title}'. Replanning.")
                    run.status = RunStatus.REPLANNING
                    run.plan = self.planner.replan(
                        goal=goal,
                        current_plan=run.plan,
                        feedback=verdict.feedback,
                        step_context=f"Failed step: {current_step.title}\nOutput: {current_step.output}",
                    )
                    step_idx = 0  # Re-evaluate from revised plan

            elif verdict.verdict == EvaluationVerdictType.REPLAN:
                run.status = RunStatus.REPLANNING
                self._log(run, "Planner", f"Evaluator triggered replan: {verdict.reason}")
                run.plan = self.planner.replan(
                    goal=goal,
                    current_plan=run.plan,
                    feedback=verdict.feedback,
                    step_context=f"Replan context: {current_step.title}\nOutput: {current_step.output}",
                )
                step_idx = 0

            elif verdict.verdict == EvaluationVerdictType.FAIL:
                current_step.status = TaskStatus.FAILED
                run.status = RunStatus.FAILED
                run.error_message = f"Execution terminated at step '{current_step.title}': {verdict.reason}"
                self._log(run, "Orchestrator", run.error_message, level="ERROR")
                break

        # 5. Finalize Run
        run.completed_at = datetime.now(timezone.utc).isoformat()
        if step_idx >= len(run.plan.steps) and run.status != RunStatus.FAILED:
            run.status = RunStatus.COMPLETED
            run.final_result = (
                f"Successfully completed all {len(run.plan.steps)} steps for goal: '{goal}'. "
                f"Plan: {run.plan.summary}"
            )
            self._log(run, "Orchestrator", "Agent run completed successfully.", level="SUCCESS")

        if self.event_callback:
            self.event_callback("complete", run)

        return run
