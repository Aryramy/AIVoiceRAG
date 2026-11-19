import os
import re
from typing import List, Dict, Any, Optional, Tuple
from rank_bm25 import BM25Okapi
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from backend.app.core.config import settings

# Global in-process Qdrant Client (persisted to data/qdrant or in-memory)
_QDRANT_DIR = os.path.join(settings.BASE_DIR, "data", "qdrant")
os.makedirs(_QDRANT_DIR, exist_ok=True)

try:
    _qdrant = QdrantClient(path=_QDRANT_DIR)
except Exception:
    _qdrant = QdrantClient(location=":memory:")

class RetrievedChunk:
    def __init__(
        self,
        chunk_id: str,
        document_id: str,
        document_title: str,
        content: str,
        page_number: Optional[int],
        score: float,
        dense_rank: Optional[int] = None,
        sparse_rank: Optional[int] = None,
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.document_title = document_title
        self.content = content
        self.page_number = page_number
        self.score = score
        self.dense_rank = dense_rank
        self.sparse_rank = sparse_rank

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_title": self.document_title,
            "content": self.content,
            "page_number": self.page_number,
            "score": round(self.score, 4),
            "dense_rank": self.dense_rank,
            "sparse_rank": self.sparse_rank,
        }

class EmbeddingService:
    def __init__(self):
        self._embedder = None
        self._dim = 384

    def _get_embedder(self):
        if self._embedder is None:
            try:
                from fastembed import TextEmbedding
                self._embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            except Exception:
                self._embedder = "fallback"
        return self._embedder

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embedder = self._get_embedder()
        if embedder != "fallback":
            try:
                embeddings = list(embedder.embed(texts))
                return [e.tolist() for e in embeddings]
            except Exception:
                pass
        
        # Deterministic lightweight n-gram hashing vectorizer for zero-crash fallback
        import hashlib
        vectors = []
        for t in texts:
            vec = [0.0] * self._dim
            tokens = re.findall(r"\w+", t.lower())
            for tok in tokens:
                h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
                idx = h % self._dim
                vec[idx] += 1.0
            # Normalize
            norm = sum(x * x for x in vec) ** 0.5
            if norm > 0:
                vec = [x / norm for x in vec]
            vectors.append(vec)
        return vectors

    def embed_query(self, query: str) -> List[float]:
        return self.embed_texts([query])[0]

_EMBEDDING_SVC = EmbeddingService()

class HybridRetrievalService:
    def __init__(self):
        self.qdrant = _qdrant
        self.embedder = _EMBEDDING_SVC
        self.dim = 384

    def _get_collection_name(self, kb_id: str) -> str:
        clean_id = kb_id.replace("-", "_")
        return f"kb_{clean_id}"

    def ensure_collection(self, kb_id: str):
        col_name = self._get_collection_name(kb_id)
        existing = [c.name for c in self.qdrant.get_collections().collections]
        if col_name not in existing:
            self.qdrant.create_collection(
                collection_name=col_name,
                vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE)
            )

    def index_chunks(self, kb_id: str, chunks_data: List[Dict[str, Any]]):
        """
        chunks_data: list of dicts with keys:
        id, doc_id, doc_title, content, page_number, chunk_index
        """
        self.ensure_collection(kb_id)
        col_name = self._get_collection_name(kb_id)

        texts = [c["content"] for c in chunks_data]
        vectors = self.embedder.embed_texts(texts)

        import uuid
        points = []
        for i, c in enumerate(chunks_data):
            # Qdrant requires valid UUID or uint64 for point ID
            raw_id = str(c["id"])
            try:
                valid_uuid = str(uuid.UUID(raw_id))
            except ValueError:
                valid_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, raw_id))

            points.append(PointStruct(
                id=valid_uuid,
                vector=vectors[i],
                payload={
                    "chunk_id": raw_id,
                    "document_id": c["doc_id"],
                    "document_title": c.get("doc_title", "Untitled"),
                    "content": c["content"],
                    "page_number": c.get("page_number"),
                    "chunk_index": c.get("chunk_index", 0)
                }
            ))

        self.qdrant.upsert(collection_name=col_name, points=points)

    def _tokenize(self, text: str) -> List[str]:
        # Handles English and Arabic words
        return re.findall(r"[\w\u0600-\u06FF]+", text.lower())

    def hybrid_search(
        self,
        kb_id: str,
        query: str,
        all_chunks: List[Dict[str, Any]],
        top_k: int = 5,
        hybrid_alpha: float = 0.6,
        similarity_threshold: float = 0.40
    ) -> List[RetrievedChunk]:
        """
        Executes Dense (Qdrant) + Sparse (BM25) search with Reciprocal Rank Fusion.
        """
        if not all_chunks:
            return []

        col_name = self._get_collection_name(kb_id)
        dense_ranks: Dict[str, int] = {}
        dense_scores: Dict[str, float] = {}

        # 1. Dense Search via Qdrant
        try:
            self.ensure_collection(kb_id)
            query_vector = self.embedder.embed_query(query)
            search_results = self.qdrant.search(
                collection_name=col_name,
                query_vector=query_vector,
                limit=top_k * 2
            )
            for rank, hit in enumerate(search_results, start=1):
                chunk_id = str(hit.payload.get("chunk_id", hit.id))
                dense_ranks[chunk_id] = rank
                dense_scores[chunk_id] = hit.score
        except Exception:
            pass

        # 2. Sparse Search via BM25
        sparse_ranks: Dict[str, int] = {}
        corpus = [self._tokenize(c["content"]) for c in all_chunks]
        tokenized_query = self._tokenize(query)

        if corpus and any(len(doc) > 0 for doc in corpus):
            bm25 = BM25Okapi(corpus)
            bm25_scores = bm25.get_scores(tokenized_query)
            # Pair with chunk IDs
            scored_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)
            for rank, idx in enumerate(scored_indices[:top_k * 2], start=1):
                if bm25_scores[idx] > 0.0:
                    chunk_id = str(all_chunks[idx]["id"])
                    sparse_ranks[chunk_id] = rank

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF_score = alpha * (1 / (60 + dense_rank)) + (1 - alpha) * (1 / (60 + sparse_rank))
        rrf_scores: Dict[str, float] = {}
        all_candidate_ids = set(dense_ranks.keys()) | set(sparse_ranks.keys())

        if not all_candidate_ids:
            # Fallback if both scores were empty (e.g. initial indexing)
            candidate_chunks = all_chunks[:top_k]
        else:
            for cid in all_candidate_ids:
                d_rank = dense_ranks.get(cid, 100)
                s_rank = sparse_ranks.get(cid, 100)
                rrf = (hybrid_alpha / (60.0 + d_rank)) + ((1.0 - hybrid_alpha) / (60.0 + s_rank))
                rrf_scores[cid] = rrf

            sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
            candidate_ids = sorted_ids[:top_k]
            chunk_lookup = {str(c["id"]): c for c in all_chunks}
            candidate_chunks = [chunk_lookup[cid] for cid in candidate_ids if cid in chunk_lookup]

        # 4. Map to RetrievedChunk objects
        results: List[RetrievedChunk] = []
        for c in candidate_chunks:
            cid = str(c["id"])
            d_rank = dense_ranks.get(cid)
            s_rank = sparse_ranks.get(cid)
            composite_score = rrf_scores.get(cid, dense_scores.get(cid, 0.5))
            
            # Normalize composite score to 0.0 - 1.0 range (max RRF score is ~1/61 = 0.0164)
            normalized_score = min(1.0, composite_score * 61.0) if cid in rrf_scores else 0.5

            if normalized_score >= similarity_threshold:
                results.append(RetrievedChunk(
                    chunk_id=cid,
                    document_id=str(c.get("document_id", c.get("doc_id", ""))),
                    document_title=str(c.get("document_title", c.get("doc_title", "Document"))),
                    content=str(c.get("content", "")),
                    page_number=c.get("page_number"),
                    score=normalized_score,
                    dense_rank=d_rank,
                    sparse_rank=s_rank
                ))

        return results

_RETRIEVAL_SVC = HybridRetrievalService()

def get_retrieval_service() -> HybridRetrievalService:
    return _RETRIEVAL_SVC
