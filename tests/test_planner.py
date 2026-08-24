from app.core.planner import Planner
from app.llm.mock_provider import MockLLMProvider
from app.tools.registry import default_tool_registry


def test_planner_create_plan():
    llm = MockLLMProvider()
    planner = Planner(llm_provider=llm, tool_registry=default_tool_registry)

    plan = planner.create_plan("Build a simple python todo app")
    assert plan.goal == "Build a simple python todo app"
    assert len(plan.steps) >= 2
    assert plan.steps[0].id == "task_1"
    assert plan.version == 1
