import pytest
from app.config import settings
from app.core.orchestrator import AgentOrchestrator
from app.llm.mock_provider import MockLLMProvider
from app.models.run_state import RunStatus


def test_agent_orchestrator_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "WORKSPACE_DIR", str(tmp_path))

    mock_llm = MockLLMProvider()
    orchestrator = AgentOrchestrator(llm_provider=mock_llm)

    run = orchestrator.run(goal="Build a prime number calculator in python and execute it")

    assert run.status == RunStatus.COMPLETED
    assert run.plan is not None
    assert len(run.plan.steps) > 0
    assert len(run.step_records) > 0
    assert run.final_result is not None
