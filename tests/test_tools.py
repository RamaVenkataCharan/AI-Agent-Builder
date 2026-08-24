import pytest
from pathlib import Path
from app.config import settings
from app.tools.code_executor import CodeExecutorTool
from app.tools.file_manager import FileManagerTool
from app.tools.registry import ToolRegistry


def test_file_manager_write_read_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "WORKSPACE_DIR", str(tmp_path))
    fm = FileManagerTool()

    # 1. Write file
    write_res = fm.execute(action="write_file", path="test_file.txt", content="Hello AI Agent Builder")
    assert write_res.success is True

    # 2. Read file
    read_res = fm.execute(action="read_file", path="test_file.txt")
    assert read_res.success is True
    assert read_res.output == "Hello AI Agent Builder"

    # 3. List dir
    list_res = fm.execute(action="list_dir", path=".")
    assert list_res.success is True
    assert "test_file.txt" in list_res.output

    # 4. Delete file
    del_res = fm.execute(action="delete_file", path="test_file.txt")
    assert del_res.success is True

    # 5. Verify deleted
    verify_res = fm.execute(action="read_file", path="test_file.txt")
    assert verify_res.success is False


def test_code_executor_python(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "WORKSPACE_DIR", str(tmp_path))
    executor = CodeExecutorTool()

    res = executor.execute(code="print('Agent Code Execution Success!')", language="python")
    assert res.success is True
    assert "Agent Code Execution Success!" in res.output


def test_tool_registry_discovery():
    registry = ToolRegistry()
    tools = registry.list_tools()
    tool_names = [t["name"] for t in tools]

    assert "file_manager" in tool_names
    assert "code_executor" in tool_names
    assert "web_search" in tool_names
    assert "data_hasher" in tool_names  # Custom tool auto-discovered!
