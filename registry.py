# tools/registry.py — Tool definitions and dispatcher

import math
import re
from pipeline import FAISSStore


class ToolRegistry:
    """
    Registers available tools and dispatches calls.
    Tools: retriever, calculator, document_info
    """

    def __init__(self, faiss_store: FAISSStore):
        self.store = faiss_store

    def retriever(self, query: str):
        """Retrieve relevant document chunks from FAISS."""
        chunks = self.store.search(query)
        if not chunks:
            return "No relevant document content found."
        return "\n\n---\n\n".join(chunks)

    def calculator(self, expression: str):
        """Safely evaluate a mathematical expression."""
        try:
            # Allow only safe math characters
            safe_expr = re.sub(r"[^0-9+\-*/().^ ]", "", expression)
            safe_expr = safe_expr.replace("^", "**")
            result = eval(safe_expr, {"__builtins__": {}}, {
                "sqrt": math.sqrt, "pi": math.pi, "e": math.e,
                "abs": abs, "round": round, "pow": pow
            })
            return f"Result: {result}"
        except Exception as ex:
            return f"Calculator error: {ex}"

    def document_info(self, _: str = ""):
        """Return metadata about the loaded document."""
        if self.store.is_empty():
            return "No document has been uploaded yet."
        return (
            f"Document is loaded. "
            f"Total chunks indexed: {len(self.store.chunks)}. "
            f"Approximate pages: {len(self.store.chunks) // 4 + 1}."
        )

    def dispatch(self, tool_name: str, tool_input: str) -> str:
        """Route a tool call to the correct handler."""
        tool_map = {
            "retriever":     self.retriever,
            "calculator":    self.calculator,
            "document_info": self.document_info,
        }
        if tool_name not in tool_map:
            return f"Unknown tool: {tool_name}"
        return tool_map[tool_name](tool_input)

    @staticmethod
    def descriptions() -> str:
        return """
Available tools:
- retriever(query): Search the uploaded PDF document for relevant information.
- calculator(expression): Evaluate a mathematical expression. E.g. calculator(12 * 3.14)
- document_info(): Get metadata about the currently loaded document.
"""
