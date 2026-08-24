from app.core.evaluator import Evaluator
from app.llm.mock_provider import MockLLMProvider
from app.models.plan import EvaluationVerdictType, TaskStep
from app.models.run_state import StepExecutionRecord


def test_evaluator_step():
    llm = MockLLMProvider()
    evaluator = Evaluator(llm_provider=llm)

    step = TaskStep(
        id="task_1",
        order=1,
        title="Create script",
        description="Write solution.py",
        expected_outcome="solution.py exists",
    )
    record = StepExecutionRecord(
        step_id="task_1",
        step_order=1,
        step_title="Create script",
        tool_used="file_manager",
        tool_status="success",
        tool_output="Successfully wrote 100 characters to solution.py",
    )

    verdict = evaluator.evaluate_step(goal="Create a script", step=step, record=record)
    assert verdict.verdict == EvaluationVerdictType.PASS
    assert verdict.score >= 0.8
