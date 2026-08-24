import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional
from app.tools.base import BaseTool, ToolResult
from app.tools.code_executor import CodeExecutorTool
from app.tools.file_manager import FileManagerTool
from app.tools.web_search import WebSearchTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry and dynamic loader for all AI Agent Builder tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
        self.discover_custom_tools()

    def _register_default_tools(self) -> None:
        self.register(FileManagerTool())
        self.register(CodeExecutorTool())
        self.register(WebSearchTool())

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance by its name."""
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieve a registered tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        """Return list of all registered tool metadata."""
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self._tools.values()
        ]

    def get_tool_descriptions_for_prompt(self) -> str:
        """Format tool descriptions for LLM system prompts."""
        lines = []
        for tool in self._tools.values():
            lines.append(f"- **{tool.name}**: {tool.description}")
        return "\n".join(lines)

    def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """Safely invoke a tool by name with arguments."""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{name}' is not registered. Available tools: {list(self._tools.keys())}",
            )
        return tool.execute(**kwargs)

    def discover_custom_tools(self, custom_dir: Optional[Path] = None) -> None:
        """Auto-discover and instantiate any BaseTool subclasses in custom/ folder."""
        if custom_dir is None:
            custom_dir = Path(__file__).parent / "custom"

        if not custom_dir.exists() or not custom_dir.is_dir():
            return

        for file_path in custom_dir.glob("*.py"):
            if file_path.name.startswith("__"):
                continue

            module_name = f"app.tools.custom.{file_path.stem}"
            try:
                module = importlib.import_module(module_name)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        inspect.isclass(attr)
                        and issubclass(attr, BaseTool)
                        and attr is not BaseTool
                    ):
                        tool_instance = attr()
                        self.register(tool_instance)
            except Exception as e:
                logger.error(f"Failed loading custom tool from {file_path}: {e}")


# Global default instance
default_tool_registry = ToolRegistry()
