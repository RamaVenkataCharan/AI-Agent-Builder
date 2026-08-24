import hashlib
import time
from typing import Any
from app.tools.base import BaseTool, ToolResult


class DataHasherTool(BaseTool):
    """Example custom tool: computes cryptographic hashes of text or metadata."""

    name: str = "data_hasher"
    description: str = (
        "Computes SHA256 or MD5 hash of input text. "
        "Parameters: 'text' (input string), 'algorithm' ('sha256' or 'md5', default 'sha256')."
    )

    def execute(self, text: str, algorithm: str = "sha256", **kwargs: Any) -> ToolResult:
        if not text:
            return ToolResult(success=False, output="", error="Parameter 'text' is required.")

        algo = algorithm.lower()
        if algo == "sha256":
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        elif algo == "md5":
            digest = hashlib.md5(text.encode("utf-8")).hexdigest()
        else:
            return ToolResult(success=False, output="", error=f"Unsupported hash algorithm '{algorithm}'.")

        return ToolResult(
            success=True,
            output=f"Algorithm: {algo.upper()}\nHash: {digest}",
            metadata={"algorithm": algo, "digest": digest, "timestamp": time.time()}
        )
