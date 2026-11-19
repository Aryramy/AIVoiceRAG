import pytest
from backend.app.services.chunking import DocumentParserAndChunker
from backend.app.services.retrieval import HybridRetrievalService

def test_chunker_text_split():
    chunker = DocumentParserAndChunker(chunk_size=100, chunk_overlap=20)
    sample_text = (
        "Enterprise Multilingual AI Voice and Knowledge Assistant.\n\n"
        "This platform provides grounded RAG search and real-time voice.\n\n"
        "It supports both Arabic and English languages with high performance."
    )
    chunks = chunker.split_text_into_chunks(sample_text, base_metadata={"test": True})
    assert len(chunks) >= 2
    assert all("test" in c.metadata for c in chunks)

def test_hybrid_search():
    retrieval_svc = HybridRetrievalService()
    kb_id = "test_kb_demo"
    
    mock_chunks = [
        {"id": "c1", "doc_id": "d1", "doc_title": "HR Policy", "content": "Employees are entitled to 25 days of paid annual leave.", "page_number": 1},
        {"id": "c2", "doc_id": "d1", "doc_title": "HR Policy", "content": "Maternity leave is provided for 12 weeks with full salary.", "page_number": 2},
        {"id": "c3", "doc_id": "d2", "doc_title": "IT Guide", "content": "VPN connections require two-factor authentication via hardware token.", "page_number": 1},
        {"id": "c4", "doc_id": "d3", "doc_title": "السياسة بالعربية", "content": "يحق لجميع الموظفين الحصول على إجازة سنوية مدفوعة الأجر قدرها 25 يوماً.", "page_number": 1}
    ]

    # Index chunks
    retrieval_svc.index_chunks(kb_id=kb_id, chunks_data=mock_chunks)

    # Search in English
    results_en = retrieval_svc.hybrid_search(
        kb_id=kb_id,
        query="annual leave policy",
        all_chunks=mock_chunks,
        top_k=2
    )
    assert len(results_en) > 0
    assert results_en[0].chunk_id in ["c1", "c4"]

    # Search in Arabic
    results_ar = retrieval_svc.hybrid_search(
        kb_id=kb_id,
        query="الإجازة السنوية",
        all_chunks=mock_chunks,
        top_k=2
    )
    assert len(results_ar) > 0
    assert results_ar[0].chunk_id in ["c4", "c1"]
