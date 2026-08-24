from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryRecord(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    score: Optional[float] = None


class BaseMemory(ABC):
    """Abstract interface for agent memory & vector storage."""

    @abstractmethod
    def add(self, doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a document or context snippet to memory."""
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 3) -> List[MemoryRecord]:
        """Search memory for relevant documents given a query string."""
        pass

    @abstractmethod
    def get_all(self) -> List[MemoryRecord]:
        """Retrieve all stored memory records."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all records in this memory store."""
        pass
