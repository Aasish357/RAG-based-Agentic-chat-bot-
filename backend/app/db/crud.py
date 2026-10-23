"""
Async CRUD operations for database models.
"""

from typing import List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import DocumentModel, MessageModel, SessionModel


async def get_or_create_session(
    db: AsyncSession, session_id: Optional[str] = None, title: Optional[str] = None
) -> SessionModel:
    """Retrieve an existing session by ID or create a new one."""
    sid = session_id or str(uuid.uuid4())
    result = await db.execute(
        select(SessionModel)
        .options(selectinload(SessionModel.messages))
        .where(SessionModel.id == sid)
    )
    session = result.scalar_one_or_none()

    if not session:
        session = SessionModel(id=sid, title=title or "New Conversation")
        db.add(session)
        await db.commit()
        await db.refresh(session)

    return session


async def update_session_summary(
    db: AsyncSession, session_id: str, rolling_summary: str
) -> None:
    """Update rolling summary for a session."""
    result = await db.execute(
        select(SessionModel).where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session:
        session.rolling_summary = rolling_summary
        await db.commit()


async def add_message(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    citations: Optional[str] = None,
) -> MessageModel:
    """Record a user or assistant message to database."""
    msg = MessageModel(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role=role,
        content=content,
        citations=citations,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_session_messages(
    db: AsyncSession, session_id: str
) -> List[MessageModel]:
    """Retrieve all messages for a session ordered chronologically."""
    result = await db.execute(
        select(MessageModel)
        .where(MessageModel.session_id == session_id)
        .order_by(MessageModel.created_at)
    )
    return list(result.scalars().all())


async def add_document(
    db: AsyncSession,
    document_id: str,
    filename: str,
    file_path: str,
    chunks_count: int,
    pages: int,
) -> DocumentModel:
    """Save metadata for an uploaded document."""
    doc = DocumentModel(
        id=document_id,
        filename=filename,
        file_path=file_path,
        chunks_count=chunks_count,
        pages=pages,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def list_documents(db: AsyncSession) -> List[DocumentModel]:
    """List all document records in the database."""
    result = await db.execute(
        select(DocumentModel).order_by(DocumentModel.uploaded_at.desc())
    )
    return list(result.scalars().all())


async def delete_document(db: AsyncSession, document_id: str) -> bool:
    """Delete a document record by ID."""
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if doc:
        await db.delete(doc)
        await db.commit()
        return True
    return False
