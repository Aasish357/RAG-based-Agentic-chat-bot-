"""Tool definitions and async dispatcher for Jahiv multi-agent pipeline."""

import math
import re
from typing import Any

try:
    from app.rag.store import list_documents, search
except ImportError:
    try:
        from backend.app.rag.store import list_documents, search
    except ImportError:
        from rag.store import list_documents, search


def calculator(expression: str) -> str:
    """Safely evaluate a mathematical expression."""
    try:
        # Allow only safe math characters
        safe_expr = re.sub(r"[^0-9+\-*/().^ ]", "", expression)
        safe_expr = safe_expr.replace("^", "**")
        result = eval(
            safe_expr,
            {"__builtins__": {}},
            {
                "sqrt": math.sqrt,
                "pi": math.pi,
                "e": math.e,
                "abs": abs,
                "round": round,
                "pow": pow,
            },
        )
        return f"Result: {result}"
    except Exception as ex:
        return f"Calculator error: {ex}"


def document_info(_: str = "") -> str:
    """Return metadata about the loaded document(s)."""
    docs = list_documents()
    if not docs:
        return "No document has been uploaded yet."
    total_chunks = sum(d.get("chunks_count", 0) for d in docs)
    doc_names = ", ".join(d.get("filename", "unknown") for d in docs)
    return (
        f"Document(s) loaded ({len(docs)}): {doc_names}. "
        f"Total chunks indexed: {total_chunks}."
    )


async def retriever(query: str) -> str:
    """Retrieve relevant document chunks from the FAISS vector store."""
    chunks = await search(query)
    if not chunks:
        return "No relevant document content found."

    parts: list[str] = []
    for c in chunks:
        if isinstance(c, dict):
            fn = c.get("filename", "")
            page = c.get("page", "")
            text = c.get("text", "")
            source = f"[{fn} | Page {page}]\n" if fn and page else ""
            parts.append(f"{source}{text}".strip())
        else:
            parts.append(str(c))
    return "\n\n---\n\n".join(parts)


async def execute_tool(tool_name: str, tool_input: str = "") -> str:
    """Route a tool call to the correct handler asynchronously."""
    name = tool_name.strip().lower()
    if name in ("retriever", "search"):
        return await retriever(tool_input)
    elif name == "calculator":
        return calculator(tool_input)
    elif name == "document_info":
        return document_info(tool_input)
    else:
        return f"Unknown tool: {tool_name}"


class ToolRegistry:
    """
    Registers available tools and dispatches calls.
    Tools: retriever, calculator, document_info
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def execute_tool(self, tool_name: str, tool_input: str = "") -> str:
        """Execute a tool asynchronously."""
        return await execute_tool(tool_name, tool_input)

    async def dispatch(self, tool_name: str, tool_input: str = "") -> str:
        """Dispatch a tool call (backward-compatible alias)."""
        return await execute_tool(tool_name, tool_input)

    @staticmethod
    def calculator(expression: str) -> str:
        return calculator(expression)

    @staticmethod
    def document_info(arg: str = "") -> str:
        return document_info(arg)

    @staticmethod
    async def retriever(query: str) -> str:
        return await retriever(query)

    @staticmethod
    def descriptions() -> str:
        return (
            "Available tools:\n"
            "- retriever(query): Search the uploaded PDF document for relevant information.\n"
            "- calculator(expression): Evaluate a mathematical expression. E.g. calculator(12 * 3.14)\n"
            "- document_info(): Get metadata about the currently loaded document.\n"
        )
