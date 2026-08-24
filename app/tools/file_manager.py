import os
from pathlib import Path
from typing import Any, Dict, Optional
from app.config import settings
from app.tools.base import BaseTool, ToolResult


class FileManagerTool(BaseTool):
    """Tool for reading, writing, creating, and listing files in the workspace."""

    name: str = "file_manager"
    description: str = (
        "Manage files inside the workspace. Supported actions: "
        "'read_file' (path), 'write_file' (path, content), "
        "'append_file' (path, content), 'list_dir' (path), 'delete_file' (path)."
    )

    def _resolve_safe_path(self, relative_path: str) -> Path:
        base = settings.workspace_path.resolve()
        # Normalize and ensure no escaping workspace
        safe_path = (base / relative_path).resolve()
        try:
            if not safe_path.is_relative_to(base):
                raise PermissionError(f"Access outside workspace directory is restricted: {relative_path}")
        except AttributeError:
            # Python < 3.9 fallback
            if not str(safe_path).startswith(str(base)):
                raise PermissionError(f"Access outside workspace directory is restricted: {relative_path}")
        return safe_path

    def execute(self, action: str, path: str = ".", content: Optional[str] = None, **kwargs: Any) -> ToolResult:
        try:
            target = self._resolve_safe_path(path)

            if action == "write_file":
                if content is None:
                    return ToolResult(success=False, output="", error="Parameter 'content' is required for write_file.")
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "w", encoding="utf-8") as f:
                    f.write(content)
                return ToolResult(
                    success=True,
                    output=f"Successfully wrote {len(content)} characters to {path}.",
                    metadata={"path": str(target), "bytes": len(content.encode('utf-8'))}
                )

            elif action == "read_file":
                if not target.exists():
                    return ToolResult(success=False, output="", error=f"File not found: {path}")
                if not target.is_file():
                    return ToolResult(success=False, output="", error=f"Path is a directory, not a file: {path}")
                with open(target, "r", encoding="utf-8", errors="replace") as f:
                    data = f.read()
                return ToolResult(success=True, output=data, metadata={"path": str(target)})

            elif action == "append_file":
                if content is None:
                    return ToolResult(success=False, output="", error="Parameter 'content' is required for append_file.")
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "a", encoding="utf-8") as f:
                    f.write(content)
                return ToolResult(success=True, output=f"Appended content to {path}.", metadata={"path": str(target)})

            elif action == "list_dir":
                if not target.exists():
                    return ToolResult(success=False, output="", error=f"Directory does not exist: {path}")
                if not target.is_dir():
                    return ToolResult(success=False, output="", error=f"Path is not a directory: {path}")

                entries = []
                for p in sorted(target.iterdir()):
                    entry_type = "DIR" if p.is_dir() else "FILE"
                    size = p.stat().st_size if p.is_file() else "-"
                    entries.append(f"[{entry_type}] {p.name} ({size} bytes)")

                out = "\n".join(entries) if entries else "(Empty directory)"
                return ToolResult(success=True, output=out, metadata={"count": len(entries)})

            elif action == "delete_file":
                if not target.exists():
                    return ToolResult(success=False, output="", error=f"File not found: {path}")
                if target.is_file():
                    target.unlink()
                    return ToolResult(success=True, output=f"Deleted file {path}.")
                else:
                    return ToolResult(success=False, output="", error=f"Cannot delete directory with delete_file: {path}")

            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unsupported action '{action}'. Valid actions: write_file, read_file, append_file, list_dir, delete_file."
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"FileManager error: {str(e)}")
