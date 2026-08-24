from typing import Any, Dict, List, Optional, Tuple
from app.memory.base import BaseMemory, MemoryRecord
from app.memory.vector_store import InMemoryVectorStore


class SessionMemory:
    """
    Manages short-term and RAG-based context memory for an active Agent execution run,
    tracking read and write operations for full run inspectability.
    """

    def __init__(self, backend: Optional[BaseMemory] = None):
        self.vector_store: BaseMemory = backend or InMemoryVectorStore()
        self._history_log: List[Dict[str, Any]] = []

    def record_step_result(
        self,
        step_id: str,
        step_title: str,
        tool_name: Optional[str],
        output: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Stores step execution outcome in vector memory and returns the document ID."""
        doc_id = f"mem_{step_id}"
        meta = metadata or {}
        meta.update({
            "step_id": step_id,
            "step_title": step_title,
            "tool_name": tool_name or "none",
        })

        content_for_rag = f"Step {step_id} ({step_title})\nTool: {tool_name}\nResult Output:\n{output}"
        self.vector_store.add(doc_id=doc_id, content=content_for_rag, metadata=meta)
        self._history_log.append({
            "doc_id": doc_id,
            "step_id": step_id,
            "title": step_title,
            "tool": tool_name,
            "output": output,
        })
        return doc_id

    def retrieve_relevant_context(self, query: str, top_k: int = 3) -> Tuple[str, List[str]]:
        """
        Retrieves relevant context snippets from memory and returns formatted text
        along with the list of retrieved memory record IDs for inspectability.
        """
        records = self.vector_store.search(query=query, top_k=top_k)
        if not records:
            return "No previous relevant context found in memory.", []

        formatted_snippets = []
        read_ids = []
        for r in records:
            read_ids.append(r.id)
            step_title = r.metadata.get("step_title", r.id)
            formatted_snippets.append(f"--- [Memory Context: {step_title} (ID: {r.id})] ---\n{r.content}")

        return "\n\n".join(formatted_snippets), read_ids

    def get_full_history(self) -> List[Dict[str, Any]]:
        return self._history_log

    def clear(self) -> None:
        self.vector_store.clear()
        self._history_log.clear()
