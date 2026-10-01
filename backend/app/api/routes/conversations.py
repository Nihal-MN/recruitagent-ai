"""Conversations + the agent chat endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.agent.orchestrator import run_turn
from app.api.deps import DbSession
from app.api.schemas import (
    ConversationCreate,
    ConversationDetail,
    ConversationOut,
    MessageIn,
    MessageOut,
    ToolExecutionOut,
    ApprovalOut,
    TurnResult,
)
from app.agent.providers import get_provider
from app.core.errors import AppError
from app.models import (
    AgentConversation,
    AgentMessage,
    ApprovalRequest,
    ToolExecution,
)
from app.services import conversations as conversations_service

router = APIRouter()


def _conversation_out(db, conversation: AgentConversation) -> ConversationOut:
    count = db.scalar(
        select(func.count(AgentMessage.id)).where(AgentMessage.conversation_id == conversation.id)
    )
    return ConversationOut(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=count or 0,
    )


def _require_conversation(db, conversation_id: int) -> AgentConversation:
    conversation = db.get(AgentConversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"No conversation with id {conversation_id}.")
    return conversation


@router.get("/conversations", response_model=list[ConversationOut], summary="List conversations")
def list_conversations(db: DbSession) -> list[ConversationOut]:
    rows = db.scalars(
        select(AgentConversation).order_by(AgentConversation.updated_at.desc()).limit(50)
    )
    return [_conversation_out(db, c) for c in rows]


@router.post(
    "/conversations",
    response_model=ConversationOut,
    status_code=201,
    summary="Create a conversation",
)
def create_conversation(payload: ConversationCreate, db: DbSession) -> ConversationOut:
    conversation = conversations_service.create_conversation(db, payload.title)
    db.commit()
    return _conversation_out(db, conversation)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    summary="Conversation with messages, tool trace and approvals",
)
def conversation_detail(conversation_id: int, db: DbSession) -> ConversationDetail:
    conversation = _require_conversation(db, conversation_id)
    messages = list(
        db.scalars(
            select(AgentMessage)
            .where(AgentMessage.conversation_id == conversation_id)
            .order_by(AgentMessage.seq)
        )
    )
    executions = list(
        db.scalars(
            select(ToolExecution)
            .where(ToolExecution.conversation_id == conversation_id)
            .order_by(ToolExecution.id)
        )
    )
    approvals = list(
        db.scalars(
            select(ApprovalRequest)
            .where(ApprovalRequest.conversation_id == conversation_id)
            .order_by(ApprovalRequest.id.desc())
        )
    )
    base = _conversation_out(db, conversation)
    return ConversationDetail(
        **base.model_dump(),
        messages=[MessageOut.model_validate(m, from_attributes=True) for m in messages],
        tool_executions=[ToolExecutionOut.model_validate(e, from_attributes=True) for e in executions],
        approvals=[ApprovalOut.model_validate(a, from_attributes=True) for a in approvals],
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=TurnResult,
    summary="Send a message — runs one bounded agent turn",
)
def send_message(conversation_id: int, payload: MessageIn, db: DbSession) -> TurnResult:
    conversation = _require_conversation(db, conversation_id)

    try:
        provider = get_provider()
    except AppError as exc:
        raise exc

    last_message_id = db.scalar(select(func.max(AgentMessage.id))) or 0
    outcome = run_turn(db, conversation, provider, payload.content)
    db.commit()

    new_message_ids = list(
        db.scalars(
            select(AgentMessage.id)
            .where(AgentMessage.id > last_message_id)
            .order_by(AgentMessage.id)
        )
    )
    return TurnResult(
        conversation_id=conversation.id,
        final_text=outcome.final_text,
        stopped_reason=outcome.stopped_reason,
        message_ids=new_message_ids,
        tool_execution_ids=outcome.tool_execution_ids,
        approval_ids=outcome.approval_ids,
        error_code=outcome.error_code,
    )
