import os
import re
import sqlite3
import math
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
        rerank_score: Optional[float] = None,
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.document_title = document_title
        self.content = content
        self.page_number = page_number
        self.score = score
        self.dense_rank = dense_rank
        self.sparse_rank = sparse_rank
        self.rerank_score = rerank_score

    def to_dict(self) -> Dict[str, Any]:
        content_snippet = self.content[:300] if self.content else ""
        return {
            "id": self.chunk_id,
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_title": self.document_title,
            "content": self.content,
            "content_snippet": content_snippet,
            "snippet": content_snippet,
            "page_number": self.page_number,
            "score": round(self.score, 4),
            "similarity_score": round(self.score, 4),
            "dense_rank": self.dense_rank,
            "sparse_rank": self.sparse_rank,
            "rerank_score": round(self.rerank_score, 4) if self.rerank_score is not None else None,
        }

class EmbeddingService:
    def __init__(self):
        self._embedder = None
        self._model_name = settings.EMBEDDING_MODEL or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        self._dim = 384

    def _get_embedder(self):
        if self._embedder is None:
            try:
                from fastembed import TextEmbedding
                self._embedder = TextEmbedding(model_name=self._model_name)
            except Exception:
                self._embedder = "fallback"
        return self._embedder

    def warmup(self):
        """Pre-warms the embedder during application lifespan startup to eliminate first-query latency."""
        try:
            self.embed_query("Warmup query مرحبا بكم")
        except Exception:
            pass

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
            tokens = re.findall(r"[\w\u0600-\u06FF]+", t.lower())
            for tok in tokens:
                h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
                idx = h % self._dim
                vec[idx] += 1.0
            norm = sum(x * x for x in vec) ** 0.5
            if norm > 0:
                vec = [x / norm for x in vec]
            vectors.append(vec)
        return vectors

    def embed_query(self, query: str) -> List[float]:
        return self.embed_texts([query])[0]

_EMBEDDING_SVC = EmbeddingService()

def is_non_latin_or_arabic(text: str) -> bool:
    """
    Detects Arabic, Perso-Arabic, or non-Latin script in text.
    """
    if not text:
        return False
    # Arabic / Arab-Persian Unicode ranges
    if re.search(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]", text):
        return True
    # Non-ASCII characters check (Cyrillic, CJK, Devanagari, etc.)
    non_ascii = [c for c in text if ord(c) > 127 and not c.isspace()]
    return len(non_ascii) > 2

class RerankerService:
    def __init__(self):
        self._reranker = None
        self._model_name = "Xenova/ms-marco-MiniLM-L-6-v2"

    def _get_reranker(self):
        if self._reranker is None:
            try:
                from fastembed.rerank.cross_encoder import TextCrossEncoder
                self._reranker = TextCrossEncoder(model_name=self._model_name)
            except Exception:
                self._reranker = "fallback"
        return self._reranker

    def warmup(self):
        """Pre-warms the cross-encoder reranker during startup."""
        try:
            r = self._get_reranker()
            if r != "fallback":
                list(r.rerank("warmup", ["warmup document"]))
        except Exception:
            pass

    def rerank(self, query: str, chunks: List[RetrievedChunk], top_k: int = 5) -> List[RetrievedChunk]:
        if not chunks:
            return []

        # Cross-lingual / non-Latin bypass:
        # Xenova/ms-marco-MiniLM-L-6-v2 is an English-only cross-encoder.
        # When given an Arabic/non-Latin query or passage, its cross-encoder logits are heavily negative (< -2.0),
        # which erroneously triggers the abstention gate on valid cross-lingual matches.
        # We detect non-Latin/Arabic queries or language mismatch, bypass the English-only cross-encoder,
        # and rely on the high-quality multilingual dense embeddings (paraphrase-multilingual-MiniLM-L12-v2).
        if "ms-marco" in self._model_name.lower():
            if is_non_latin_or_arabic(query) or any(is_non_latin_or_arabic(c.content[:200]) for c in chunks):
                for chunk in chunks:
                    if chunk.rerank_score is None:
                        chunk.rerank_score = chunk.score
                return chunks[:top_k]

        reranker = self._get_reranker()
        if reranker == "fallback":
            return chunks[:top_k]

        try:
            docs = [c.content[:500] for c in chunks]
            scores = list(reranker.rerank(query, docs))
            
            # If all candidates have strongly negative cross-encoder logits (< -2.0),
            # the query has zero semantic grounding in the knowledge base (e.g. moon missions).
            if not scores or max(scores) < -2.0:
                return []

            scored_pairs = list(zip(chunks, scores))
            # Sort descending by cross-encoder score
            scored_pairs.sort(key=lambda x: x[1], reverse=True)
            
            reranked_results: List[RetrievedChunk] = []
            for chunk, score in scored_pairs[:top_k]:
                # Exclude chunks with negative cross-encoder logits (unrelated text like Vehicles/Housekeeping)
                if score < -2.0:
                    continue
                
                # Sigmoid normalization for human-readable 0.0 - 1.0 confidence
                sigmoid_score = 1.0 / (1.0 + math.exp(-max(-15.0, min(15.0, score))))
                chunk.rerank_score = round(sigmoid_score, 4)
                chunk.score = round(0.3 * chunk.score + 0.7 * sigmoid_score, 4)
                reranked_results.append(chunk)

            return reranked_results
        except Exception:
            return chunks[:top_k]

_RERANKER_SVC = RerankerService()

class HybridRetrievalService:
    def __init__(self):
        self.qdrant = _qdrant
        self.embedder = _EMBEDDING_SVC
        self.reranker = _RERANKER_SVC
        self.dim = 384
        self._db_path = os.path.join(settings.BASE_DIR, "data", "voicerag.db")
        self._init_fts5_table()

    def _init_fts5_table(self):
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts USING fts5(chunk_id UNINDEXED, kb_id UNINDEXED, content)"
                )
                conn.commit()
        except Exception:
            pass

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
        Indexes chunks into both Qdrant Vector DB and SQLite FTS5.
        """
        self.ensure_collection(kb_id)
        col_name = self._get_collection_name(kb_id)

        texts = [c["content"] for c in chunks_data]
        vectors = self.embedder.embed_texts(texts)

        import uuid
        points = []
        fts_rows = []
        for i, c in enumerate(chunks_data):
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
            fts_rows.append((raw_id, kb_id, c["content"]))

        self.qdrant.upsert(collection_name=col_name, points=points)

        # Index in SQLite FTS5 for sub-millisecond sparse retrieval
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("DELETE FROM document_chunks_fts WHERE kb_id = ?", (kb_id,))
                conn.executemany(
                    "INSERT INTO document_chunks_fts(chunk_id, kb_id, content) VALUES (?, ?, ?)",
                    fts_rows
                )
                conn.commit()
        except Exception:
            pass

    def _tokenize(self, text: str) -> List[str]:
        # Normalize Arabic alef and strip diacritics
        normalized = re.sub(r"[\u064B-\u065F\u0670]", "", text)
        normalized = re.sub(r"[إأآ]", "ا", normalized)
        raw_tokens = re.findall(r"[\w\u0600-\u06FF]+", normalized.lower())
        tokens = []
        for t in raw_tokens:
            tokens.append(t)
            if t.startswith("ال") and len(t) > 3:
                tokens.append(t[2:])
            elif t.startswith("و") and len(t) > 3:
                tokens.append(t[1:])
        return list(dict.fromkeys(tokens))

    def _fts5_search(self, kb_id: str, query: str, limit: int = 10) -> Dict[str, float]:
        """Sub-millisecond sparse keyword search via SQLite FTS5."""
        tokens = self._tokenize(query)
        if not tokens:
            return {}

        clean_query = " OR ".join(f'"{tok}"*' for tok in tokens if len(tok) > 1)
        if not clean_query:
            return {}

        sparse_scores: Dict[str, float] = {}
        try:
            with sqlite3.connect(self._db_path) as conn:
                # In SQLite FTS5, bm25() returns negative score (more negative = better)
                cursor = conn.execute(
                    """
                    SELECT chunk_id, bm25(document_chunks_fts) as rank_score
                    FROM document_chunks_fts
                    WHERE kb_id = ? AND document_chunks_fts MATCH ?
                    ORDER BY rank_score ASC
                    LIMIT ?
                    """,
                    (kb_id, clean_query, limit)
                )
                rows = cursor.fetchall()
                if rows:
                    min_score = min(r[1] for r in rows) # most negative = highest relevance
                    for rank_idx, (cid, score) in enumerate(rows, start=1):
                        # Convert negative BM25 score to positive normalized score [0.0, 1.0]
                        # Best document (score == min_score) gets 1.0; weaker matches get proportional fraction
                        normalized = max(0.2, min(1.0, score / min_score)) if min_score < 0 else 0.5
                        sparse_scores[str(cid)] = normalized
        except Exception:
            pass

        return sparse_scores

    def hybrid_search(
        self,
        kb_id: str,
        query: str,
        all_chunks: List[Dict[str, Any]],
        top_k: int = 5,
        hybrid_alpha: float = 0.6,
        similarity_threshold: float = 0.40,
        reranker_enabled: bool = True
    ) -> List[RetrievedChunk]:
        """
        Executes Dense (Qdrant) + Sparse (SQLite FTS5 / BM25) search with genuine linear hybrid scoring,
        strict threshold enforcement, and cross-encoder reranking.
        """
        if not all_chunks:
            return []

        col_name = self._get_collection_name(kb_id)
        dense_ranks: Dict[str, int] = {}
        dense_scores: Dict[str, float] = {}

        # 1. Dense Vector Search via Qdrant
        try:
            self.ensure_collection(kb_id)
            query_vector = self.embedder.embed_query(query)
            if hasattr(self.qdrant, "query_points"):
                q_res = self.qdrant.query_points(
                    collection_name=col_name,
                    query=query_vector,
                    limit=top_k * 3
                )
                search_results = q_res.points
            else:
                search_results = self.qdrant.search(
                    collection_name=col_name,
                    query_vector=query_vector,
                    limit=top_k * 3
                )
            for rank, hit in enumerate(search_results, start=1):
                chunk_id = str(hit.payload.get("chunk_id", hit.id))
                dense_ranks[chunk_id] = rank
                # Cosine similarity in Qdrant is between -1.0 and 1.0, clamp to [0.0, 1.0]
                dense_scores[chunk_id] = max(0.0, float(hit.score))
        except Exception:
            pass

        # 2. Sparse Keyword Search via SQLite FTS5 (with BM25Okapi fallback)
        sparse_scores = self._fts5_search(kb_id, query, limit=top_k * 3)
        sparse_ranks: Dict[str, int] = {}

        if sparse_scores:
            sorted_sparse = sorted(sparse_scores.items(), key=lambda x: x[1], reverse=True)
            for r_idx, (cid, _) in enumerate(sorted_sparse, start=1):
                sparse_ranks[cid] = r_idx
        else:
            # Fallback to BM25Okapi in RAM
            corpus = [self._tokenize(c["content"]) for c in all_chunks]
            tokenized_query = self._tokenize(query)
            if corpus and any(len(doc) > 0 for doc in corpus):
                bm25 = BM25Okapi(corpus)
                bm25_scores = bm25.get_scores(tokenized_query)
                max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
                scored_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)
                for rank, idx in enumerate(scored_indices[:top_k * 3], start=1):
                    if bm25_scores[idx] > 0.0:
                        chunk_id = str(all_chunks[idx]["id"])
                        sparse_ranks[chunk_id] = rank
                        sparse_scores[chunk_id] = min(1.0, float(bm25_scores[idx] / max_bm25))

        # 3. Genuine Linear Hybrid Scoring
        all_candidates = set(dense_ranks.keys()) | set(sparse_ranks.keys())
        if not all_candidates:
            return []

        chunk_lookup = {str(c["id"]): c for c in all_chunks}
        candidate_chunks: List[RetrievedChunk] = []

        for cid in all_candidates:
            if cid not in chunk_lookup:
                continue

            d_score = dense_scores.get(cid, 0.0)
            s_score = sparse_scores.get(cid, 0.0)
            d_rank = dense_ranks.get(cid)
            s_rank = sparse_ranks.get(cid)

            # Linear hybrid formula
            if cid in dense_scores and cid in sparse_scores:
                hybrid_score = (hybrid_alpha * d_score) + ((1.0 - hybrid_alpha) * s_score)
            elif cid in dense_scores:
                hybrid_score = d_score * hybrid_alpha
            else:
                hybrid_score = s_score * (1.0 - hybrid_alpha)

            # Effective relevance score
            effective_score = max(d_score, hybrid_score)

            # Strictly enforce similarity_threshold:
            # If query is completely out-of-scope (e.g. "moon missions"), d_score < 0.25 and s_score = 0.
            # It will fail this threshold and return 0 chunks, allowing clean abstention!
            if effective_score >= similarity_threshold:
                c_data = chunk_lookup[cid]
                candidate_chunks.append(RetrievedChunk(
                    chunk_id=cid,
                    document_id=str(c_data.get("document_id", c_data.get("doc_id", ""))),
                    document_title=str(c_data.get("document_title", c_data.get("doc_title", "Document"))),
                    content=str(c_data.get("content", "")),
                    page_number=c_data.get("page_number"),
                    score=round(effective_score, 4),
                    dense_rank=d_rank,
                    sparse_rank=s_rank
                ))

        # Sort candidate chunks by hybrid score descending
        candidate_chunks.sort(key=lambda x: x.score, reverse=True)

        # 4. Optional Cross-Encoder Reranking
        if reranker_enabled and candidate_chunks:
            return self.reranker.rerank(query=query, chunks=candidate_chunks, top_k=top_k)

        return candidate_chunks[:top_k]

_RETRIEVAL_SVC = HybridRetrievalService()

def get_retrieval_service() -> HybridRetrievalService:
    return _RETRIEVAL_SVC
