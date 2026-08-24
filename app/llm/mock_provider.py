import json
import logging
from typing import Optional
from app.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class MockLLMProvider(BaseLLMProvider):
    """
    Mock LLM Provider for offline testing, CI/CD, and demonstrations.
    Intelligently responds to Planning, Execution, and Evaluation prompts.
    """

    def __init__(self, model: str = "mock-agent-v1", temperature: float = 0.0):
        super().__init__(model=model, temperature=temperature)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        prompt_lower = prompt.lower()
        sys_lower = (system_prompt or "").lower()

        # Check if this is a Planning request
        if "break this goal into an actionable sequence of tasks" in prompt_lower or "decompose" in prompt_lower or "planner" in sys_lower:
            return json.dumps({
                "summary": "Plan decomposed into environment setup, implementation, validation, and summary.",
                "steps": [
                    {
                        "id": "task_1",
                        "order": 1,
                        "title": "Analyze Goal and Inspect Workspace",
                        "description": "Examine the workspace directory and identify existing files or configuration requirements.",
                        "suggested_tool": "file_manager",
                        "tool_input_hint": {"action": "list_dir", "path": "."},
                        "expected_outcome": "List of current workspace files and directories."
                    },
                    {
                        "id": "task_2",
                        "order": 2,
                        "title": "Generate Core Implementation File",
                        "description": "Create the primary script/file based on user instructions and specifications.",
                        "suggested_tool": "file_manager",
                        "tool_input_hint": {
                            "action": "write_file",
                            "path": "solution.py",
                            "content": "# Solution script\ndef run():\n    print('Task accomplished successfully!')\n\nif __name__ == '__main__':\n    run()\n"
                        },
                        "expected_outcome": "Executable script created in workspace."
                    },
                    {
                        "id": "task_3",
                        "order": 3,
                        "title": "Execute and Verify Output",
                        "description": "Run the generated script and capture outputs to verify proper behavior.",
                        "suggested_tool": "code_executor",
                        "tool_input_hint": {"code": "python solution.py", "language": "shell"},
                        "expected_outcome": "Script executed with returncode 0 and valid output."
                    }
                ]
            }, indent=2)

        # Check if this is an Evaluation request
        if "evaluate" in prompt_lower or "evaluator" in sys_lower:
            return json.dumps({
                "verdict": "pass",
                "score": 0.95,
                "feedback": "The task output satisfies the required acceptance criteria without any errors.",
                "suggested_action": "Proceed to the next task in the execution queue."
            }, indent=2)

        # Default generic response
        return "I have analyzed the request and processed the instructions successfully."
