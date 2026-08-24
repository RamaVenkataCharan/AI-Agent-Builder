import json
import logging
from typing import Optional
from app.llm.base import BaseLLMProvider
from app.memory.session_memory import SessionMemory
from app.models.plan import Plan, TaskStep
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are an expert AI Planner. Your job is to break down a high-level user goal into an ordered, actionable sequence of discrete tasks (TaskSteps) with explicit dependencies.

Available Tools:
{tools_description}

Guidelines:
1. Decompose the goal into logical stages (e.g., workspace inspection, implementation/creation, execution/testing, summary).
2. Explicitly declare any prerequisite step IDs in `dependencies` (e.g. `["task_1"]`).
3. Recommend the best matching `suggested_tool` from the available tools for each step.
4. Define a clear, objective `expected_outcome` (acceptance criteria) for each task so the Evaluator can verify it strictly against the output.
5. Provide a concise `summary` of the plan.

Output strictly as a JSON object matching this schema:
{{
  "summary": "High-level description of what the plan achieves",
  "steps": [
    {{
      "id": "task_1",
      "order": 1,
      "title": "Task title",
      "description": "Specific instruction of what to do",
      "dependencies": [],
      "suggested_tool": "file_manager",
      "tool_input_hint": {{"action": "write_file", "path": "app.py", "content": "..."}},
      "expected_outcome": "Explicit criteria that must be verified by the evaluator"
    }}
  ]
}}
"""

REPLAN_SYSTEM_PROMPT = """You are an expert AI Planner reviewing an active plan that requires replanning based on an evaluator's feedback and execution failure.

Available Tools:
{tools_description}

Goal: {goal}
Original Plan Version: {version}
Evaluator Feedback / Reason for Replan: {feedback}
Completed or Failed Step Context:
{step_context}

Create a revised, corrected plan to achieve the goal starting from the current state.
Output strictly JSON matching the Plan schema.
"""


class Planner:
    """Decomposes goals into actionable plans and generates revised plans on replanning."""

    def __init__(self, llm_provider: BaseLLMProvider, tool_registry: ToolRegistry):
        self.llm = llm_provider
        self.tool_registry = tool_registry

    def create_plan(self, goal: str, memory: Optional[SessionMemory] = None) -> Plan:
        """Create a new plan from a user goal."""
        tools_desc = self.tool_registry.get_tool_descriptions_for_prompt()
        system_prompt = PLANNER_SYSTEM_PROMPT.format(tools_description=tools_desc)

        user_prompt = f"Goal: {goal}"
        if memory:
            context, _ = memory.retrieve_relevant_context(query=goal, top_k=2)
            if "No previous" not in context:
                user_prompt += f"\n\nExisting Memory Context:\n{context}"

        try:
            data = self.llm.generate_json(prompt=user_prompt, system_prompt=system_prompt)
            steps = []
            for i, s in enumerate(data.get("steps", []), 1):
                steps.append(
                    TaskStep(
                        id=s.get("id", f"task_{i}"),
                        order=s.get("order", i),
                        title=s.get("title", f"Step {i}"),
                        description=s.get("description", ""),
                        dependencies=s.get("dependencies", [f"task_{i-1}"] if i > 1 else []),
                        suggested_tool=s.get("suggested_tool"),
                        tool_input_hint=s.get("tool_input_hint"),
                        expected_outcome=s.get("expected_outcome", "Complete task step successfully and verify output."),
                    )
                )

            return Plan(
                goal=goal,
                summary=data.get("summary", f"Plan for: {goal}"),
                steps=steps,
                version=1,
            )
        except Exception as e:
            logger.error(f"Planner generation failed: {e}. Generating default fallback plan.")
            return Plan(
                goal=goal,
                summary=f"Automated execution plan for: {goal}",
                steps=[
                    TaskStep(
                        id="task_1",
                        order=1,
                        title="Execute Goal Task",
                        description=f"Accomplish goal: {goal}",
                        dependencies=[],
                        suggested_tool="file_manager",
                        tool_input_hint={"action": "list_dir", "path": "."},
                        expected_outcome="Goal steps executed in workspace directory.",
                    )
                ],
                version=1,
            )

    def replan(
        self,
        goal: str,
        current_plan: Plan,
        feedback: str,
        step_context: str,
    ) -> Plan:
        """Generate a revised plan after an evaluation failure or replan trigger."""
        tools_desc = self.tool_registry.get_tool_descriptions_for_prompt()
        system_prompt = REPLAN_SYSTEM_PROMPT.format(
            tools_description=tools_desc,
            goal=goal,
            version=current_plan.version,
            feedback=feedback,
            step_context=step_context,
        )

        user_prompt = "Generate the revised step sequence to overcome the failure and achieve the goal."

        try:
            data = self.llm.generate_json(prompt=user_prompt, system_prompt=system_prompt)
            steps = []
            for i, s in enumerate(data.get("steps", []), 1):
                steps.append(
                    TaskStep(
                        id=s.get("id", f"revised_task_{i}"),
                        order=s.get("order", i),
                        title=s.get("title", f"Revised Step {i}"),
                        description=s.get("description", ""),
                        dependencies=s.get("dependencies", [f"revised_task_{i-1}"] if i > 1 else []),
                        suggested_tool=s.get("suggested_tool"),
                        tool_input_hint=s.get("tool_input_hint"),
                        expected_outcome=s.get("expected_outcome", "Complete revised task"),
                    )
                )

            return Plan(
                goal=goal,
                summary=data.get("summary", f"Revised Plan (v{current_plan.version + 1})"),
                steps=steps,
                version=current_plan.version + 1,
            )
        except Exception as e:
            logger.error(f"Replanning error: {e}")
            current_plan.version += 1
            return current_plan
