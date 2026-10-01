"""Conversation persistence helpers — coherent sessions without model memory."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentConversation, AgentMessage

MAX_TITLE = 120


def create_conversation(db: Session, title: str | None = None) -> AgentConversation:
    conversation = AgentConversation(title=(title or "New conversation")[:MAX_TITLE])
    db.add(conversation)
    db.flush()
    return conversation


def append_message(
    db: Session,
    conversation: AgentConversation,
    role: str,
    content: str,
    *,
    tool_execution_id: int | None = None,
) -> AgentMessage:
    next_seq = (
        db.scalar(
            select(AgentMessage.seq)
            .where(AgentMessage.conversation_id == conversation.id)
            .order_by(AgentMessage.seq.desc())
            .limit(1)
        )
        or 0
    ) + 1
    message = AgentMessage(
        conversation_id=conversation.id,
        seq=next_seq,
        role=role,
        content=content,
        tool_execution_id=tool_execution_id,
    )
    db.add(message)
    db.flush()
    if role == "user" and next_seq == 1:
        conversation.title = content.strip()[:MAX_TITLE] or "New conversation"
        if tool_execution_id is None and next_seq == 1:
            from app.services import activity

            activity.log(
                db,
                "conversation_started",
                f"Conversation started: \u201c{conversation.title}\u201d",
                conversation_id=conversation.id,
            )
    return message


def recent_messages(db: Session, conversation_id: int, limit: int = 12) -> list[AgentMessage]:
    rows = list(
        db.scalars(
            select(AgentMessage)
            .where(AgentMessage.conversation_id == conversation_id)
            .order_by(AgentMessage.seq.desc())
            .limit(limit)
        )
    )
    return list(reversed(rows))
