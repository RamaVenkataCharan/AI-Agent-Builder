import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseLLMProvider(ABC):
    """Abstract interface for all LLM providers (Ollama, OpenAI, Mock)."""

    def __init__(self, model: str, temperature: float = 0.2):
        self.model = model
        self.temperature = temperature

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate text completion for a given prompt."""
        pass

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Type[T]] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Generate structured JSON response, extracting and parsing JSON block.
        """
        format_instruction = (
            "\nYou must respond STRICTLY with valid JSON. "
            "Do not include markdown code fences (like ```json), commentary, or explanation outside the JSON object."
        )
        full_system_prompt = (system_prompt or "") + format_instruction

        response_text = self.generate(
            prompt=prompt,
            system_prompt=full_system_prompt,
            temperature=temperature if temperature is not None else self.temperature,
        )

        return self._extract_json(response_text)

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON object from LLM response text, handling code blocks or noisy text."""
        cleaned = text.strip()

        # Try direct parse
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown ```json ... ``` or ``` ... ```
        json_fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if json_fence_match:
            try:
                return json.loads(json_fence_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding outer braces { ... }
        brace_match = re.search(r"(\{[\s\S]*\})", cleaned)
        if brace_match:
            try:
                return json.loads(brace_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding outer array [ ... ]
        bracket_match = re.search(r"(\[[\s\S]*\])", cleaned)
        if bracket_match:
            try:
                return {"items": json.loads(bracket_match.group(1).strip())}
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Failed to extract valid JSON from LLM output: {text[:300]}...")
