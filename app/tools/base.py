from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    name: str
    description: str

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool action with supplied arguments."""
        pass

    def get_schema(self) -> Dict[str, Any]:
        """Return parameter schema description for LLM prompts."""
        return {
            "name": self.name,
            "description": self.description,
        }
