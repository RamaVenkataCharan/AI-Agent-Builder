"""
End-to-end Demonstration Script for AI Agent Builder
Demonstrates:
1. Goal formulation
2. Plan decomposition with dependencies
3. Autonomous multi-tool execution (file_manager, code_executor)
4. Evaluator reflection and criteria verification
5. RAG Memory persistence
6. Real file generated in ./workspace/fibonacci.py
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from app.config import settings
from app.core.orchestrator import AgentOrchestrator
from app.llm.mock_provider import MockLLMProvider
from app.tools.registry import default_tool_registry


class FibonacciGoalMockLLM(MockLLMProvider):
    """Specialized mock returning precise steps for the Fibonacci goal."""

    def generate(self, prompt: str, system_prompt: str = None, temperature: float = None) -> str:
        prompt_lower = prompt.lower()
        sys_lower = (system_prompt or "").lower()

        if "break down a high-level user goal" in sys_lower or "planner" in sys_lower:
            return json.dumps({
                "summary": "Implement, persist, execute, and verify a Fibonacci sequence generator.",
                "steps": [
                    {
                        "id": "task_1",
                        "order": 1,
                        "title": "Create Fibonacci Calculator Script",
                        "description": "Write a Python script that computes the first 10 Fibonacci numbers and prints them.",
                        "dependencies": [],
                        "suggested_tool": "file_manager",
                        "tool_input_hint": {
                            "action": "write_file",
                            "path": "fibonacci.py",
                            "content": (
                                "def fibonacci(n):\n"
                                "    sequence = [0, 1]\n"
                                "    while len(sequence) < n:\n"
                                "        sequence.append(sequence[-1] + sequence[-2])\n"
                                "    return sequence[:n]\n\n"
                                "if __name__ == '__main__':\n"
                                "    res = fibonacci(10)\n"
                                "    print(f'Fibonacci(10): {res}')\n"
                            )
                        },
                        "expected_outcome": "fibonacci.py written successfully to workspace"
                    },
                    {
                        "id": "task_2",
                        "order": 2,
                        "title": "Execute Fibonacci Script and Verify Output",
                        "description": "Run the fibonacci.py script using Python executor and capture output.",
                        "dependencies": ["task_1"],
                        "suggested_tool": "code_executor",
                        "tool_input_hint": {
                            "code": "python fibonacci.py",
                            "language": "shell"
                        },
                        "expected_outcome": "Script runs with exit code 0 and outputs [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]"
                    }
                ]
            })

        if "evaluator" in sys_lower or "skeptical evaluator" in sys_lower:
            return json.dumps({
                "verdict": "pass",
                "score": 0.98,
                "reason": "Execution strictly satisfied acceptance criteria.",
                "feedback": "The tool successfully created and executed the script with valid Fibonacci output.",
                "suggested_action": "Proceed to next step."
            })

        return super().generate(prompt, system_prompt, temperature)


def run_demo():
    goal = "Create a python script that calculates fibonacci sequence and save it to workspace as fibonacci.py, then execute it and verify output."
    print("=" * 70)
    print(f"DISPATCHING GOAL:\n'{goal}'")
    print("=" * 70)

    llm = FibonacciGoalMockLLM()
    orchestrator = AgentOrchestrator(
        llm_provider=llm,
        tool_registry=default_tool_registry,
    )

    run = orchestrator.run(goal=goal)

    print(f"\n[RUN RESULT] Status: {run.status.value.upper()} (ID: {run.run_id})")
    print(f"Plan Summary: {run.plan.summary}")
    print(f"Total Steps: {len(run.plan.steps)}")

    print("\n--- STEP EXECUTION TIMELINE ---")
    for rec in run.step_records:
        print(f"\nStep {rec.step_order}: {rec.step_title}")
        print(f"  Tool: {rec.tool_used} ({rec.duration_seconds}s)")
        print(f"  Tool Reasoning: {rec.tool_selection_reasoning}")
        print(f"  Tool Output: {rec.tool_output.strip()}")
        print(f"  Evaluator Verdict: {rec.evaluation.verdict.value.upper()} (Score: {rec.evaluation.score})")
        print(f"  Evaluator Reason: {rec.evaluation.reason}")
        print(f"  Memory Writes: {rec.memory_writes}")

    # Inspect generated workspace file
    fib_file = settings.workspace_path / "fibonacci.py"
    print("\n--- WORKSPACE FILE VERIFICATION ---")
    print(f"File Path: {fib_file}")
    print(f"Exists: {fib_file.exists()}")
    if fib_file.exists():
        print(f"Content:\n{fib_file.read_text(encoding='utf-8')}")


if __name__ == "__main__":
    run_demo()
