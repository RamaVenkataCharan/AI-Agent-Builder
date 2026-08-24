import logging
from typing import Optional
from app.config import settings
from app.llm.base import BaseLLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


def get_llm_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
) -> BaseLLMProvider:
    """
    Factory function returning the configured LLM provider instance.
    Supports 'ollama', 'openai', and 'mock'.
    """
    prov = (provider_name or settings.LLM_PROVIDER).lower()
    mod = model or settings.LLM_MODEL
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE

    if prov == "ollama":
        return OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=mod,
            temperature=temp,
        )
    elif prov in ("openai", "chatgpt"):
        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            model=mod,
            temperature=temp,
        )
    elif prov == "mock":
        return MockLLMProvider(model=mod, temperature=temp)
    else:
        logger.warning(f"Unknown LLM provider '{prov}'. Falling back to Ollama.")
        return OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=mod,
            temperature=temp,
        )
