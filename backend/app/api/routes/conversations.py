from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.database.models import Conversation, Message, MessageCitation
from backend.app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    CitationResponse
)
from backend.app.services.rag import get_rag_service

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("", response_model=List[ConversationResponse])
def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    convs = (
        db.query(Conversation)
        .order_by(desc(Conversation.updated_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    results = []
    for c in convs:
        count = db.query(Message).filter(Message.conversation_id == c.id).count()
        results.append(ConversationResponse(
            id=c.id,
            user_id=c.user_id,
            title=c.title,
            language=c.language,
            created_at=c.created_at,
            updated_at=c.updated_at,
            message_count=count
        ))
    return results

@router.post("", response_model=ConversationResponse)
def create_conversation(data: ConversationCreate, db: Session = Depends(get_db)):
    conv = Conversation(
        title=data.title or "New Conversation",
        language=data.language or "en"
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ConversationResponse(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        language=conv.language,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=0
    )

@router.get("/{conversation_id}")
def get_conversation_details(conversation_id: str, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    msg_responses = []
    for m in messages:
        citations = db.query(MessageCitation).filter(MessageCitation.message_id == m.id).all()
        cit_dtos = [
            CitationResponse(
                id=c.id,
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_title=c.document_title,
                page_number=c.page_number,
                content_snippet=c.content_snippet,
                similarity_score=c.similarity_score
            )
            for c in citations
        ]
        msg_responses.append(MessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            language=m.language,
            provider=m.provider,
            model=m.model,
            latency_ms=m.latency_ms,
            cost_usd=m.cost_usd,
            prompt_tokens=m.prompt_tokens,
            completion_tokens=m.completion_tokens,
            total_tokens=m.total_tokens,
            created_at=m.created_at,
            citations=cit_dtos
        ))

    return {
        "id": conv.id,
        "title": conv.title,
        "language": conv.language,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "messages": msg_responses
    }

@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Delete child messages and citations
    msgs = db.query(Message).filter(Message.conversation_id == conversation_id).all()
    for m in msgs:
        db.query(MessageCitation).filter(MessageCitation.message_id == m.id).delete()
        db.delete(m)
    
    db.delete(conv)
    db.commit()
    return {"success": True, "message": "Conversation deleted"}

@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    data: MessageCreate,
    knowledge_base_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    rag = get_rag_service()
    result = await rag.answer_query(
        db=db,
        conversation_id=conversation_id,
        user_query=data.content,
        kb_id=knowledge_base_id,
        language=data.language or conv.language
    )

    # Auto-update conversation title if it's the first message
    msg_count = db.query(Message).filter(Message.conversation_id == conversation_id).count()
    if msg_count <= 2:
        clean_snippet = data.content.strip().split("\n")[0][:40]
        conv.title = clean_snippet if len(clean_snippet) > 3 else conv.title
        db.commit()

    return result
