import json
import logging
from typing import Optional
import httpx
from app.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """LLM Provider for local Ollama instances."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3:latest",
        temperature: float = 0.2,
        timeout: float = 120.0,
    ):
        super().__init__(model=model, temperature=temperature)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama at {self.base_url}. Ensure Ollama is running.")
            raise RuntimeError(f"Ollama connection error: Could not reach {self.base_url}. Is Ollama started?") from e
        except Exception as e:
            logger.error(f"Ollama request error: {e}")
            raise RuntimeError(f"Ollama generation failed: {e}") from e
