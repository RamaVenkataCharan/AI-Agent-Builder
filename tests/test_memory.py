import pytest
from app.memory.session_memory import SessionMemory
from app.memory.vector_store import InMemoryVectorStore


def test_in_memory_vector_store():
    store = InMemoryVectorStore()
    store.add(doc_id="doc1", content="Building a python fast api application with sqlite")
    store.add(doc_id="doc2", content="Frontend React UI with Tailwind CSS and vite")
    store.add(doc_id="doc3", content="Database migrations and docker container setup")

    results = store.search(query="fastapi backend api", top_k=1)
    assert len(results) == 1
    assert results[0].id == "doc1"


def test_session_memory_retrieval():
    mem = SessionMemory()
    doc_id = mem.record_step_result(
        step_id="step_1",
        step_title="Initialize Workspace",
        tool_name="file_manager",
        output="Created main.py and requirements.txt",
    )
    assert doc_id == "mem_step_1"

    context, read_ids = mem.retrieve_relevant_context("requirements and setup", top_k=1)
    assert "Created main.py" in context
    assert "mem_step_1" in read_ids
