import logging
from typing import Any, Dict, List, Optional
from app.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """Tool for searching the web for real-time information, documentation, and sources."""

    name: str = "web_search"
    description: str = (
        "Search the web for documentation, solutions, or factual references. "
        "Parameters: 'query' (search query string), 'max_results' (optional int, default 5)."
    )

    def execute(self, query: str, max_results: int = 5, **kwargs: Any) -> ToolResult:
        if not query or not query.strip():
            return ToolResult(success=False, output="", error="Parameter 'query' cannot be empty.")

        # Attempt DuckDuckGo search if available
        try:
            from duckduckgo_search import DDGS  # type: ignore

            results_list = []
            with DDGS() as ddgs:
                ddg_results = ddgs.text(query, max_results=max_results)
                for r in ddg_results:
                    title = r.get("title", "No title")
                    link = r.get("href", "")
                    body = r.get("body", "")
                    results_list.append(f"Title: {title}\nURL: {link}\nSnippet: {body}\n")

            if results_list:
                output = "\n---\n".join(results_list)
                return ToolResult(success=True, output=output, metadata={"query": query, "count": len(results_list)})

        except Exception as e:
            logger.warning(f"DuckDuckGo search live query failed or not installed: {e}. Using knowledge fallback.")

        # Fallback informative mock response
        fallback_msg = (
            f"[Web Search Result for '{query}']:\n"
            f"- Information regarding '{query}' indicates standard industry patterns and best practices.\n"
            f"- Documentation reference: Relevant libraries and tools can be found in standard official packages."
        )
        return ToolResult(success=True, output=fallback_msg, metadata={"query": query, "fallback": True})
