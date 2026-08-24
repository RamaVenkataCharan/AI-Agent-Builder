import json
import logging
import time
from typing import Any, Dict, Optional, Tuple
from app.llm.base import BaseLLMProvider
from app.memory.session_memory import SessionMemory
from app.models.plan import TaskStep
from app.models.run_state import StepExecutionRecord
from app.tools.base import ToolResult
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

EXECUTOR_SYSTEM_PROMPT = """You are the Tool Calling Executor of an autonomous AI Agent framework.
Your task is to review a specific TaskStep, consider previous memory context, select the best tool, explain your reasoning, and formulate the exact JSON parameters needed to invoke that tool.

Available Tools:
{tools_description}

Output strictly as a JSON object with:
{{
  "tool_name": "name_of_selected_tool",
  "tool_parameters": {{
     "param1": "value1"
  }},
  "rationale": "Explicit rationale for why this tool and parameters were chosen"
}}
"""


class Executor:
    """Autonomous execution engine that executes single TaskSteps using tools."""

    def __init__(self, llm_provider: BaseLLMProvider, tool_registry: ToolRegistry):
        self.llm = llm_provider
        self.tool_registry = tool_registry

    def execute_step(
        self,
        step: TaskStep,
        memory: SessionMemory,
        goal: str,
    ) -> StepExecutionRecord:
        """Executes a single task step using the appropriate tool and records reasoning."""
        start_time = time.time()
        record = StepExecutionRecord(
            step_id=step.id,
            step_order=step.order,
            step_title=step.title,
        )

        # 1. Decide on tool and parameters with reasoning
        tool_name = step.suggested_tool
        tool_params: Dict[str, Any] = step.tool_input_hint or {}
        reasoning: Optional[str] = f"Selected {tool_name} based on step plan recommendation."
        read_memory_ids = []

        if not tool_name or not tool_params:
            tool_name, tool_params, reasoning, read_memory_ids = self._synthesize_tool_invocation(step, memory, goal)
        else:
            # Check memory for relevant context
            _, read_memory_ids = memory.retrieve_relevant_context(query=step.description, top_k=2)

        record.tool_used = tool_name
        record.tool_inputs = tool_params
        record.tool_selection_reasoning = reasoning
        record.memory_reads = read_memory_ids

        # 2. Invoke Tool via Registry
        if tool_name:
            tool_result: ToolResult = self.tool_registry.execute_tool(tool_name, **tool_params)
            record.tool_status = "success" if tool_result.success else "error"
            record.tool_output = tool_result.output if tool_result.success else (tool_result.error or "Unknown error")
        else:
            record.tool_status = "error"
            record.tool_output = "No valid tool selected for this step."

        # 3. Finalize execution record timing
        duration = time.time() - start_time
        record.duration_seconds = round(duration, 3)

        # 4. Store result in session memory for subsequent steps & record write ID
        write_doc_id = memory.record_step_result(
            step_id=step.id,
            step_title=step.title,
            tool_name=tool_name,
            output=record.tool_output or "",
            metadata={"status": record.tool_status, "order": step.order},
        )
        record.memory_writes = [write_doc_id]

        return record

    def _synthesize_tool_invocation(
        self,
        step: TaskStep,
        memory: SessionMemory,
        goal: str,
    ) -> Tuple[Optional[str], Dict[str, Any], str, list[str]]:
        """Query LLM to dynamically determine tool name, parameters, and rationale."""
        tools_desc = self.tool_registry.get_tool_descriptions_for_prompt()
        system_prompt = EXECUTOR_SYSTEM_PROMPT.format(tools_description=tools_desc)

        relevant_context, read_ids = memory.retrieve_relevant_context(query=step.description, top_k=2)

        user_prompt = (
            f"Overall Goal: {goal}\n"
            f"Current Task Step {step.order}: {step.title}\n"
            f"Instructions: {step.description}\n"
            f"Expected Outcome: {step.expected_outcome}\n"
            f"Context from Earlier Steps:\n{relevant_context}\n"
        )

        try:
            decision = self.llm.generate_json(prompt=user_prompt, system_prompt=system_prompt)
            tool_name = decision.get("tool_name")
            tool_params = decision.get("tool_parameters", {})
            reasoning = decision.get("rationale", f"Synthesized invocation for tool '{tool_name}' to satisfy step outcome.")
            return tool_name, tool_params, reasoning, read_ids
        except Exception as e:
            logger.warning(f"Failed to synthesize tool invocation via LLM: {e}")
            return (
                step.suggested_tool or "file_manager",
                step.tool_input_hint or {"action": "list_dir", "path": "."},
                f"Fallback execution for {step.suggested_tool or 'file_manager'}",
                read_ids,
            )
