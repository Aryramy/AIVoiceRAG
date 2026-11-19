import os
import shutil
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.database.models import KnowledgeBase, Document, DocumentChunk
from backend.app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    DocumentResponse,
    RetrievalQueryRequest,
    RetrievalResultResponse
)
from backend.app.services.chunking import get_chunker
from backend.app.services.retrieval import get_retrieval_service

router = APIRouter(prefix="/knowledge-bases", tags=["Knowledge"])

_UPLOADS_DIR = os.path.join(settings.BASE_DIR, "data", "uploads")
os.makedirs(_UPLOADS_DIR, exist_ok=True)

@router.get("", response_model=List[KnowledgeBaseResponse])
def list_knowledge_bases(db: Session = Depends(get_db)):
    kbs = db.query(KnowledgeBase).order_by(desc(KnowledgeBase.created_at)).all()
    results = []
    for kb in kbs:
        doc_count = db.query(Document).filter(Document.knowledge_base_id == kb.id).count()
        chunk_count = (
            db.query(DocumentChunk)
            .join(Document, DocumentChunk.document_id == Document.id)
            .filter(Document.knowledge_base_id == kb.id)
            .count()
        )
        results.append(KnowledgeBaseResponse(
            id=kb.id,
            user_id=kb.user_id,
            name=kb.name,
            description=kb.description,
            language=kb.language,
            created_at=kb.created_at,
            updated_at=kb.updated_at,
            document_count=doc_count,
            chunk_count=chunk_count
        ))
    return results

@router.post("", response_model=KnowledgeBaseResponse)
def create_knowledge_base(data: KnowledgeBaseCreate, db: Session = Depends(get_db)):
    kb = KnowledgeBase(
        name=data.name,
        description=data.description,
        language=data.language or "multilingual"
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    
    # Initialize Qdrant collection
    retrieval_svc = get_retrieval_service()
    retrieval_svc.ensure_collection(kb.id)

    return KnowledgeBaseResponse(
        id=kb.id,
        user_id=kb.user_id,
        name=kb.name,
        description=kb.description,
        language=kb.language,
        created_at=kb.created_at,
        updated_at=kb.updated_at,
        document_count=0,
        chunk_count=0
    )

@router.get("/{kb_id}")
def get_knowledge_base_details(kb_id: str, db: Session = Depends(get_db)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    docs = db.query(Document).filter(Document.knowledge_base_id == kb_id).order_by(desc(Document.created_at)).all()
    doc_dtos = [
        DocumentResponse(
            id=d.id,
            knowledge_base_id=d.knowledge_base_id,
            title=d.title,
            file_name=d.file_name,
            file_type=d.file_type,
            file_size_bytes=d.file_size_bytes,
            status=d.status,
            chunk_count=d.chunk_count,
            language=d.language,
            created_at=d.created_at
        )
        for d in docs
    ]

    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "language": kb.language,
        "created_at": kb.created_at,
        "documents": doc_dtos
    }

@router.delete("/{kb_id}")
def delete_knowledge_base(kb_id: str, db: Session = Depends(get_db)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # Delete documents and chunks
    docs = db.query(Document).filter(Document.knowledge_base_id == kb_id).all()
    for d in docs:
        db.query(DocumentChunk).filter(DocumentChunk.document_id == d.id).delete()
        db.delete(d)

    db.delete(kb)
    db.commit()
    return {"success": True, "message": "Knowledge base deleted"}

@router.post("/{kb_id}/documents/upload")
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # Save uploaded file
    file_ext = os.path.splitext(file.filename)[1].lower()
    saved_filename = f"{uuid.uuid4()}_{file.filename}"
    saved_path = os.path.join(_UPLOADS_DIR, saved_filename)

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(saved_path)

    # Create document record
    doc = Document(
        knowledge_base_id=kb_id,
        title=file.filename,
        file_name=file.filename,
        file_type=file_ext.replace(".", ""),
        file_size_bytes=file_size,
        file_path=saved_path,
        status="processing"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        # Extract and chunk
        chunker = get_chunker()
        chunks_dto = chunker.process_file(saved_path)
        
        chunks_to_index = []
        for c in chunks_dto:
            page_num = c.metadata.get("page")
            db_chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=c.chunk_index,
                content=c.content,
                page_number=page_num,
                token_count=len(c.content.split())
            )
            db.add(db_chunk)
            db.flush()

            chunks_to_index.append({
                "id": db_chunk.id,
                "doc_id": doc.id,
                "doc_title": doc.title,
                "content": c.content,
                "page_number": page_num,
                "chunk_index": c.chunk_index
            })

        # Index in Qdrant
        retrieval_svc = get_retrieval_service()
        retrieval_svc.index_chunks(kb_id=kb_id, chunks_data=chunks_to_index)

        doc.chunk_count = len(chunks_dto)
        doc.status = "indexed"
        db.commit()

        return {
            "success": True,
            "document_id": doc.id,
            "title": doc.title,
            "chunks_count": len(chunks_dto),
            "status": "indexed"
        }

    except Exception as e:
        doc.status = "failed"
        doc.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

@router.delete("/{kb_id}/documents/{doc_id}")
def delete_document(kb_id: str, doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.knowledge_base_id == kb_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass

    db.delete(doc)
    db.commit()
    return {"success": True, "message": "Document deleted"}

@router.post("/{kb_id}/query", response_model=List[RetrievalResultResponse])
def query_knowledge_base(
    kb_id: str,
    query_data: RetrievalQueryRequest,
    db: Session = Depends(get_db)
):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    db_chunks = (
        db.query(DocumentChunk, Document.title)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(Document.knowledge_base_id == kb_id)
        .all()
    )

    chunk_dicts = [
        {
            "id": c.DocumentChunk.id,
            "doc_id": c.DocumentChunk.document_id,
            "doc_title": c.title,
            "content": c.DocumentChunk.content,
            "page_number": c.DocumentChunk.page_number,
            "chunk_index": c.DocumentChunk.chunk_index
        }
        for c in db_chunks
    ]

    retrieval_svc = get_retrieval_service()
    results = retrieval_svc.hybrid_search(
        kb_id=kb_id,
        query=query_data.query,
        all_chunks=chunk_dicts,
        top_k=query_data.top_k,
        hybrid_alpha=query_data.hybrid_alpha,
        similarity_threshold=query_data.similarity_threshold
    )

    return [
        RetrievalResultResponse(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            document_title=r.document_title,
            content=r.content,
            page_number=r.page_number,
            score=r.score,
            dense_rank=r.dense_rank,
            sparse_rank=r.sparse_rank
        )
        for r in results
    ]

