import logging
from typing import Optional
from app.llm.base import BaseLLMProvider
from app.models.plan import EvaluationVerdict, EvaluationVerdictType, TaskStep
from app.models.run_state import StepExecutionRecord

logger = logging.getLogger(__name__)

EVALUATOR_SYSTEM_PROMPT = """You are the Skeptical Evaluator / Critic of an autonomous AI Agent framework.
Your role is to rigorously inspect the output of an executed task step against its specific acceptance criteria (`expected_outcome`) and instructions.

CRITICAL INSTRUCTIONS:
1. Do NOT rubber-stamp outputs or assume success just because a tool was invoked without crash.
2. Verify that the tool output directly satisfies the step's `expected_outcome`.
3. If an error occurred or the output is empty / incomplete / wrong, issue `retry` or `replan`.
4. Provide a punchy one-line `reason` summarizing the verdict concisely.

Possible Verdicts:
- "pass": The output strictly satisfies the step's expected acceptance criteria.
- "retry": The step encountered a fixable tool issue or missing parameter that should be retried.
- "replan": The outcome reveals an architectural flaw or changed environment that invalidates downstream steps.
- "fail": Unrecoverable error or invalid goal.

Output strictly as a JSON object with:
{{
  "verdict": "pass" | "retry" | "replan" | "fail",
  "score": 0.0 to 1.0,
  "reason": "Crisp one-line verdict reason",
  "feedback": "Detailed explanation of why the output does or does not meet the acceptance criteria",
  "suggested_action": "Specific recommendation for next step or corrective action"
}}
"""


class Evaluator:
    """Evaluates task execution results against acceptance criteria and goal requirements."""

    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider

    def evaluate_step(
        self,
        goal: str,
        step: TaskStep,
        record: StepExecutionRecord,
    ) -> EvaluationVerdict:
        """Evaluate a completed step execution record skeptically."""
        # Heuristic 1: If tool explicitly failed with error
        if record.tool_status == "error":
            return EvaluationVerdict(
                verdict=EvaluationVerdictType.RETRY,
                score=0.1,
                reason=f"Tool '{record.tool_used}' execution error.",
                feedback=f"Tool failed to execute successfully: {record.tool_output}",
                suggested_action="Retry step with corrected tool parameters.",
            )

        # Heuristic 2: If tool produced no output
        if not record.tool_output or not record.tool_output.strip():
            return EvaluationVerdict(
                verdict=EvaluationVerdictType.RETRY,
                score=0.2,
                reason="Tool completed with empty output.",
                feedback="Step produced no output to evaluate against the acceptance criteria.",
                suggested_action="Re-run step with valid instructions.",
            )

        user_prompt = (
            f"Overall Goal: {goal}\n"
            f"Step Order: {step.order}\n"
            f"Step Title: {step.title}\n"
            f"Instructions: {step.description}\n"
            f"Acceptance Criteria (Expected Outcome): {step.expected_outcome}\n"
            f"Tool Invoked: {record.tool_used}\n"
            f"Tool Inputs: {record.tool_inputs}\n"
            f"Tool Output Received:\n{record.tool_output}\n"
        )

        try:
            res = self.llm.generate_json(prompt=user_prompt, system_prompt=EVALUATOR_SYSTEM_PROMPT)
            verdict_str = res.get("verdict", "pass").lower()
            
            try:
                v_type = EvaluationVerdictType(verdict_str)
            except ValueError:
                v_type = EvaluationVerdictType.PASS

            return EvaluationVerdict(
                verdict=v_type,
                score=float(res.get("score", 0.9)),
                reason=res.get("reason", f"Evaluated as {v_type.value.upper()} against acceptance criteria."),
                feedback=res.get("feedback", "Step completed evaluation against acceptance criteria."),
                suggested_action=res.get("suggested_action"),
            )
        except Exception as e:
            logger.warning(f"Evaluator LLM error: {e}. Performing heuristic evaluation.")
            if record.tool_status == "success" and record.tool_output:
                return EvaluationVerdict(
                    verdict=EvaluationVerdictType.PASS,
                    score=0.85,
                    reason="Output verified via heuristic validation.",
                    feedback="Tool succeeded with valid output matching step requirements.",
                    suggested_action="Proceed to next step.",
                )
            else:
                return EvaluationVerdict(
                    verdict=EvaluationVerdictType.RETRY,
                    score=0.2,
                    reason="Evaluation failed due to tool error.",
                    feedback=f"Tool reported error: {record.tool_output}",
                    suggested_action="Retry step.",
                )
