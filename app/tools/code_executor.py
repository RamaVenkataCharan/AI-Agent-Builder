import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
from app.config import settings
from app.tools.base import BaseTool, ToolResult


class CodeExecutorTool(BaseTool):
    """Tool for executing Python scripts or shell commands safely within workspace."""

    name: str = "code_executor"
    description: str = (
        "Execute Python code snippets or shell commands in the workspace. "
        "Parameters: 'code' (string of code or command to run), "
        "'language' ('python' or 'shell', default 'python'), "
        "'timeout' (optional seconds, default 60)."
    )

    def execute(
        self,
        code: str,
        language: str = "python",
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> ToolResult:
        if not code or not code.strip():
            return ToolResult(success=False, output="", error="No code provided for execution.")

        exec_timeout = timeout or settings.STEP_TIMEOUT_SECONDS
        cwd = settings.workspace_path

        try:
            if language.lower() in ("python", "py"):
                # Run python script in workspace
                result = subprocess.run(
                    [sys.executable, "-c", code],
                    cwd=str(cwd),
                    capture_output=True,
                    text=True,
                    timeout=exec_timeout,
                )
            elif language.lower() in ("shell", "bash", "cmd", "powershell"):
                result = subprocess.run(
                    code,
                    shell=True,
                    cwd=str(cwd),
                    capture_output=True,
                    text=True,
                    timeout=exec_timeout,
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unsupported language '{language}'. Supported: 'python', 'shell'."
                )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            returncode = result.returncode

            combined_output = []
            if stdout:
                combined_output.append(f"STDOUT:\n{stdout}")
            if stderr:
                combined_output.append(f"STDERR:\n{stderr}")

            out_text = "\n\n".join(combined_output) if combined_output else "(Execution finished with no output)"

            is_success = (returncode == 0)
            return ToolResult(
                success=is_success,
                output=out_text,
                error=None if is_success else f"Process exited with non-zero code {returncode}.",
                metadata={"returncode": returncode, "language": language}
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error=f"Execution timed out after {exec_timeout} seconds."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Code execution error: {str(e)}"
            )
