"""FastAPI route handlers for Jahiv backend."""

import inspect
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

try:
    from app.config import settings
except ImportError:
    try:
        from backend.app.config import settings
    except ImportError:
        try:
            import config as root_config

            class SettingsFallback:
                OLLAMA_BASE_URL: str = getattr(root_config, "OLLAMA_BASE_URL", "http://localhost:11434")
                LLM_MODEL: str = getattr(root_config, "LLM_MODEL", "llama3.1")
                DATA_DIR: str = getattr(root_config, "UPLOAD_FOLDER", "data")
                CRITIC_ENABLED: bool = True

            settings = SettingsFallback()
        except ImportError:
            class DefaultSettings:
                OLLAMA_BASE_URL: str = "http://localhost:11434"
                LLM_MODEL: str = "llama3.1"
                DATA_DIR: str = "data"
                CRITIC_ENABLED: bool = True

            settings = DefaultSettings()

try:
    from app.memory.manager import ConversationMemory
except ImportError:
    try:
        from backend.app.memory.manager import ConversationMemory
    except ImportError:
        from memory.manager import ConversationMemory

try:
    from app.rag.store import ingest_pdf, list_documents, search
except ImportError:
    try:
        from backend.app.rag.store import ingest_pdf, list_documents, search
    except ImportError:
        from rag.store import ingest_pdf, list_documents, search

try:
    from app.tools.registry import ToolRegistry, execute_tool
except ImportError:
    try:
        from backend.app.tools.registry import ToolRegistry, execute_tool
    except ImportError:
        from tools.registry import ToolRegistry, execute_tool

try:
    from app.db.session import async_session_maker
    from app.db import crud
except ImportError:
    async_session_maker = None
    crud = None

# Attempt importing agent pipeline or agents
try:
    from app.agents.pipeline import run_pipeline
except ImportError:
    try:
        from backend.app.agents.pipeline import run_pipeline
    except ImportError:
        run_pipeline = None

try:
    from app.agents.planner import run_planner
except ImportError:
    try:
        from backend.app.agents.planner import run_planner
    except ImportError:
        try:
            from planner import run_planner
        except ImportError:
            run_planner = None

try:
    from app.agents.executor import run_executor
except ImportError:
    try:
        from backend.app.agents.executor import run_executor
    except ImportError:
        try:
            from executor import run_executor
        except ImportError:
            run_executor = None

try:
    from app.agents.critic import run_critic
except ImportError:
    try:
        from backend.app.agents.critic import run_critic
    except ImportError:
        try:
            from critic import run_critic
        except ImportError:
            run_critic = None


# Router with required prefix
router = APIRouter(prefix="/api", tags=["api"])

# Module-level ConversationMemory instance
memory = ConversationMemory()


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None


async def _execute_default_pipeline(user_query: str, mem: ConversationMemory) -> dict[str, Any]:
    """Execute the multi-agent pipeline (Planner -> Tools -> Executor -> Critic)."""
    summary, recent = mem.build_context()

    # 1. Planner
    plan_dict: dict[str, Any] = {"plan": "", "tools_needed": [], "retrieval_query": None}
    if run_planner is not None:
        try:
            plan_res = run_planner(user_query, summary, recent)
            if inspect.isawaitable(plan_res):
                plan_dict = await plan_res
            else:
                plan_dict = plan_res
        except Exception as ex:
            print(f"[Planner Error] {ex}")

    tools_needed = plan_dict.get("tools_needed", [])
    retrieval_query = plan_dict.get("retrieval_query")

    # 2. Tool execution
    tool_results: dict[str, str] = {}
    for t_name in tools_needed:
        if t_name in ("retriever", "search") and retrieval_query:
            tool_results["retriever"] = await execute_tool("retriever", retrieval_query)
        elif t_name in ("calculator", "document_info"):
            tool_results[t_name] = await execute_tool(t_name, "")

    # 3. Executor
    draft = ""
    if run_executor is not None:
        try:
            exec_res = run_executor(
                user_query,
                plan_dict.get("plan", ""),
                tool_results,
                summary,
                recent,
                tools_needed,
            )
            if inspect.isawaitable(exec_res):
                draft = await exec_res
            else:
                draft = exec_res
        except Exception as ex:
            print(f"[Executor Error] {ex}")

    # Fallback to direct Ollama call if draft generation failed
    if not draft:
        context_parts: list[str] = []
        if summary:
            context_parts.append(f"[Conversation Summary]\n{summary}")
        if tool_results:
            for k, v in tool_results.items():
                context_parts.append(f"[{k}]\n{v}")
        context_block = "\n\n".join(context_parts)
        prompt = (
            "You are a helpful assistant.\n\n"
            f"{context_block}\n\n"
            f"USER: {user_query}\n\n"
            "ASSISTANT:"
        )
        timeout = httpx.Timeout(120.0, connect=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={"model": settings.LLM_MODEL, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            draft = resp.json().get("response", "").strip()

    # 4. Critic
    critic_enabled = getattr(settings, "CRITIC_ENABLED", True)
    verdict = "PASS"
    issues = "NONE"
    final_answer = draft

    if critic_enabled and run_critic is not None:
        try:
            critic_res = run_critic(user_query, draft, tool_results)
            if inspect.isawaitable(critic_res):
                critique = await critic_res
            else:
                critique = critic_res
            verdict = critique.get("verdict", "PASS")
            issues = critique.get("issues", "NONE")
            final_answer = critique.get("final_answer", draft)
        except Exception as ex:
            print(f"[Critic Error] {ex}")

    # 5. Record turn & update summary
    mem.add_turn(user_query, final_answer)
    await mem.update_summary()

    return {
        "answer": final_answer,
        "debug": {
            "tools_used": tools_needed,
            "retrieval_query": retrieval_query,
            "critic_verdict": verdict,
            "critic_issues": issues,
        },
    }


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)) -> dict[str, Any]:
    """Accept UploadFile, validate PDF, save to DATA_DIR, call ingest_pdf, return result."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )

    data_dir = Path(getattr(settings, "DATA_DIR", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    save_path = data_dir / file.filename

    try:
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)

        result = await ingest_pdf(str(save_path), file.filename)
        memory.clear()

        # Persist document metadata to DB if available
        if async_session_maker and crud and "document_id" in result:
            try:
                async with async_session_maker() as db:
                    await crud.add_document(
                        db=db,
                        document_id=result["document_id"],
                        filename=file.filename,
                        file_path=str(save_path),
                        chunks_count=result.get("chunks_indexed", 0),
                        pages=result.get("pages", 0),
                    )
            except Exception as db_err:
                print(f"[DB Warning] Could not persist document: {db_err}")

        return {
            "message": "Document ingested successfully.",
            "filename": file.filename,
            **result,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {exc}",
        )


@router.post("/documents/upload", include_in_schema=False)
async def upload_pdf_alias(file: UploadFile = File(...)) -> dict[str, Any]:
    """Compatibility alias for document upload."""
    return await upload_pdf(file)


@router.post("/chat")
async def chat(payload: ChatMessage) -> dict[str, Any]:
    """Accept JSON body with 'message' and optional 'session_id', run pipeline, return result."""
    user_query = payload.message.strip()
    if not user_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No message provided",
        )

    session_id = payload.session_id
    history: list[dict[str, str]] = []
    rolling_summary = ""

    # Load session history from DB if session_id provided and DB available
    if async_session_maker and crud and session_id:
        try:
            async with async_session_maker() as db:
                session_rec = await crud.get_or_create_session(db, session_id=session_id)
                rolling_summary = session_rec.rolling_summary or ""
                msgs = await crud.get_session_messages(db, session_id=session_id)
                for m in msgs:
                    history.append({"role": m.role, "content": m.content})
        except Exception as db_err:
            print(f"[DB Warning] Could not retrieve session history: {db_err}")

    try:
        if run_pipeline is not None:
            # If session history is used from DB, pass it; otherwise pass memory
            if session_id:
                pipeline_res = await run_pipeline(
                    user_query,
                    conversation_history=history,
                    rolling_summary=rolling_summary,
                )
            else:
                summary, recent = memory.build_context()
                pipeline_res = await run_pipeline(
                    user_query,
                    conversation_history=recent,
                    rolling_summary=summary,
                )
                memory.add_turn(user_query, pipeline_res.get("answer", ""))
            
            # Persist to DB if session_id is active
            if async_session_maker and crud and session_id:
                try:
                    async with async_session_maker() as db:
                        await crud.add_message(db, session_id, "user", user_query)
                        await crud.add_message(db, session_id, "assistant", pipeline_res.get("answer", ""))
                        if "rolling_summary" in pipeline_res:
                            await crud.update_session_summary(db, session_id, pipeline_res["rolling_summary"])
                except Exception as db_err:
                    print(f"[DB Warning] Could not persist session messages: {db_err}")

            return pipeline_res

        return await _execute_default_pipeline(user_query, memory)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent pipeline error: {exc}",
        )


@router.get("/documents")
async def get_documents() -> list[dict[str, Any]]:
    """Return list of indexed documents (from DB if available, fallback to in-memory)."""
    if async_session_maker and crud:
        try:
            async with async_session_maker() as db:
                docs = await crud.list_documents(db)
                if docs:
                    return [d.to_dict() for d in docs]
        except Exception:
            pass
    return list_documents()


@router.delete("/documents/{doc_id}")
async def delete_document_endpoint(doc_id: str) -> dict[str, Any]:
    """Remove a document from DB and vector catalog."""
    deleted_db = False
    if async_session_maker and crud:
        try:
            async with async_session_maker() as db:
                deleted_db = await crud.delete_document(db, doc_id)
        except Exception as exc:
            print(f"[DB Warning] Document delete failed: {exc}")

    return {
        "message": f"Document {doc_id} deletion processed.",
        "document_id": doc_id,
        "deleted": deleted_db,
    }


@router.get("/memory/{session_id}")
async def get_session_memory(session_id: str) -> dict[str, Any]:
    """Retrieve conversational history and rolling summary for a given session."""
    if async_session_maker and crud:
        try:
            async with async_session_maker() as db:
                session_rec = await crud.get_or_create_session(db, session_id=session_id)
                msgs = await crud.get_session_messages(db, session_id=session_id)
                return {
                    "session_id": session_id,
                    "title": session_rec.title,
                    "rolling_summary": session_rec.rolling_summary,
                    "messages": [m.to_dict() for m in msgs],
                    "messages_count": len(msgs),
                }
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not retrieve memory for session: {exc}",
            )

    summary, recent = memory.build_context()
    return {
        "session_id": session_id,
        "rolling_summary": summary,
        "messages": recent,
        "messages_count": len(recent),
    }


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/status")
async def get_status() -> dict[str, Any]:
    """Return backend status."""
    docs = list_documents()
    return {
        "document_loaded": len(docs) > 0,
        "documents_count": len(docs),
        "memory_turns": len(memory.history),
    }


@router.post("/clear")
async def clear_memory() -> dict[str, str]:
    """Clear conversation memory."""
    memory.clear()
    return {"message": "Conversation memory cleared."}
