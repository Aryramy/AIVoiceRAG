from typing import List, Optional
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.database.models import Conversation, Message, MessageCitation
from backend.app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
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
            knowledge_base_id=c.knowledge_base_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
            message_count=count
        ))
    return results

@router.post("", response_model=ConversationResponse)
def create_conversation(data: ConversationCreate, db: Session = Depends(get_db)):
    conv = Conversation(
        title=data.title or "New Conversation",
        language=data.language or "en",
        knowledge_base_id=data.knowledge_base_id
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ConversationResponse(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        language=conv.language,
        knowledge_base_id=conv.knowledge_base_id,
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
                content=c.content_snippet,
                citation_index=c.citation_index,
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
        "knowledge_base_id": conv.knowledge_base_id,
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

@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: str,
    data: ConversationUpdate,
    db: Session = Depends(get_db)
):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    dump = data.model_dump(exclude_unset=True)
    if "title" in dump:
        conv.title = dump["title"]
    if "language" in dump:
        conv.language = dump["language"]
    if "knowledge_base_id" in dump:
        val = dump["knowledge_base_id"]
        if val in ("", "null", "none", None):
            conv.knowledge_base_id = None
        else:
            conv.knowledge_base_id = str(val).strip()

    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conv)

    count = db.query(Message).filter(Message.conversation_id == conv.id).count()
    return ConversationResponse(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        language=conv.language,
        knowledge_base_id=conv.knowledge_base_id,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=count
    )

@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    data: MessageCreate,
    knowledge_base_id: Optional[str] = Query(None),
    use_rag: Optional[bool] = Query(None),
    is_voice: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Determine use_rag
    effective_use_rag = True
    if use_rag is not None:
        effective_use_rag = use_rag
    elif data.use_rag is not None:
        effective_use_rag = data.use_rag

    effective_is_voice = is_voice if is_voice is not None else bool(data.is_voice)

    # Determine target_kb
    if not effective_use_rag:
        target_kb = None
    else:
        req_kb = knowledge_base_id if knowledge_base_id is not None else data.knowledge_base_id
        if req_kb is not None:
            if str(req_kb).strip().lower() in ("", "null", "none"):
                target_kb = None
            else:
                target_kb = str(req_kb).strip()
        else:
            target_kb = conv.knowledge_base_id

    rag = get_rag_service()
    result = await rag.answer_query(
        db=db,
        conversation_id=conversation_id,
        user_query=data.content,
        kb_id=target_kb,
        language=data.language or conv.language,
        use_rag=bool(effective_use_rag and target_kb),
        is_voice=effective_is_voice
    )

    # Auto-update conversation title if it's the first message
    msg_count = db.query(Message).filter(Message.conversation_id == conversation_id).count()
    if msg_count <= 2:
        clean_snippet = data.content.strip().split("\n")[0][:40]
        conv.title = clean_snippet if len(clean_snippet) > 3 else conv.title
        db.commit()

    return result

@router.post("/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: str,
    data: MessageCreate,
    knowledge_base_id: Optional[str] = Query(None),
    use_rag: Optional[bool] = Query(None),
    is_voice: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Determine use_rag
    effective_use_rag = True
    if use_rag is not None:
        effective_use_rag = use_rag
    elif data.use_rag is not None:
        effective_use_rag = data.use_rag

    effective_is_voice = is_voice if is_voice is not None else bool(data.is_voice)

    # Determine target_kb
    if not effective_use_rag:
        target_kb = None
    else:
        req_kb = knowledge_base_id if knowledge_base_id is not None else data.knowledge_base_id
        if req_kb is not None:
            if str(req_kb).strip().lower() in ("", "null", "none"):
                target_kb = None
            else:
                target_kb = str(req_kb).strip()
        else:
            target_kb = conv.knowledge_base_id

    rag = get_rag_service()

    async def sse_event_generator():
        async for event in rag.answer_query_stream(
            db=db,
            conversation_id=conversation_id,
            user_query=data.content,
            kb_id=target_kb,
            language=data.language or conv.language,
            use_rag=bool(effective_use_rag and target_kb),
            is_voice=effective_is_voice
        ):
            yield f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"

    # Auto-update conversation title if it's the first message
    msg_count = db.query(Message).filter(Message.conversation_id == conversation_id).count()
    if msg_count <= 2:
        clean_snippet = data.content.strip().split("\n")[0][:40]
        conv.title = clean_snippet if len(clean_snippet) > 3 else conv.title
        db.commit()

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "Content-Type": "text/event-stream"
    }
    return StreamingResponse(sse_event_generator(), media_type="text/event-stream", headers=headers)


