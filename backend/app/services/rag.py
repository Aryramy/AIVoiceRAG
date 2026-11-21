import time
import uuid
import re
import json
from typing import Dict, Any, List, Optional, Tuple, AsyncIterator
from sqlalchemy.orm import Session

from backend.app.database.models import (
    Conversation, Message, KnowledgeBase, Document, DocumentChunk, MessageCitation, AISettings, UsageLog
)
from backend.app.services.intent import get_intent_classifier, UserIntent
from backend.app.services.retrieval import get_retrieval_service, RetrievedChunk
from backend.app.services.router import get_router
from backend.app.services.pricing import get_pricing_calculator
from backend.app.integrations import get_provider_adapter
from backend.app.schemas.settings import AISettingsResponse

class RAGService:
    def __init__(self):
        self.intent_classifier = get_intent_classifier()
        self.retrieval_svc = get_retrieval_service()
        self.router = get_router()
        self.pricing_calc = get_pricing_calculator()

    def get_or_create_settings(self, db: Session, user_id: Optional[str] = None) -> AISettings:
        settings_record = db.query(AISettings).first()
        if not settings_record:
            settings_record = AISettings()
            db.add(settings_record)
            db.commit()
            db.refresh(settings_record)
        return settings_record

    def _filter_grounded_citations(
        self,
        retrieved_chunks: List[RetrievedChunk],
        assistant_content: str,
        assistant_msg_id: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Extracts cited source indices ([1], [2], etc.) from the assistant's answer and only
        attaches chunks that were actually referenced. If no bracket markers exist,
        only attaches chunks with high rerank confidence (>= 0.85).
        """
        # Extract cited indices: supports single [1], multiple [1][2], and grouped comma-separated [2, 3] or [1, 2, 3]
        cited_indices = set()
        for bracket_content in re.findall(r"\[([0-9\s,–-]+)\]", assistant_content):
            for num_str in re.findall(r"\d+", bracket_content):
                try:
                    cited_indices.add(int(num_str))
                except ValueError:
                    pass
        citations_data = []

        for idx, rc in enumerate(retrieved_chunks, start=1):
            is_cited = idx in cited_indices
            if is_cited or (not cited_indices and (rc.rerank_score or rc.score) >= 0.85):
                cit = MessageCitation(
                    message_id=assistant_msg_id,
                    chunk_id=rc.chunk_id,
                    document_id=rc.document_id,
                    document_title=rc.document_title,
                    page_number=rc.page_number,
                    content_snippet=rc.content[:300] if rc.content else "",
                    similarity_score=rc.score,
                    citation_index=idx
                )
                db.add(cit)
                c_dict = rc.to_dict()
                c_dict["citation_index"] = idx
                citations_data.append(c_dict)

        db.commit()
        return citations_data

    async def answer_query(
        self,
        db: Session,
        conversation_id: str,
        user_query: str,
        kb_id: Optional[str] = None,
        language: Optional[str] = None,
        stream: bool = False,
        use_rag: bool = True,
        is_voice: bool = False
    ) -> Dict[str, Any]:
        # Strict scope isolation: if use_rag is False or kb_id is empty/null, strictly skip retrieval
        if not use_rag or kb_id in (None, "", "null", "none", "None"):
            kb_id = None

        start_time = time.perf_counter()
        t_db_start = time.perf_counter()
        settings_model = self.get_or_create_settings(db)
        settings_dto = AISettingsResponse.model_validate(settings_model)
        db_ms = round((time.perf_counter() - t_db_start) * 1000, 2)

        t_intent_start = time.perf_counter()
        # Script-first language detection:
        if re.search(r"[\u0600-\u06FF]", user_query):
            is_ar = True
        elif re.search(r"[A-Za-z]", user_query):
            is_ar = False
        else:
            is_ar = bool(language and language.lower().startswith("ar"))
        intent, canned_response = self.intent_classifier.classify(user_query)
        intent_ms = round((time.perf_counter() - t_intent_start) * 1000, 2)

        # 1. Handle pure conversational intent (only when no specific KB is requested)
        if intent == UserIntent.CONVERSATIONAL and not kb_id:
            latency = round((time.perf_counter() - start_time) * 1000, 2)
            assistant_text = canned_response or ("Hello! How can I assist you?" if not is_ar else "مرحباً! كيف أستطيع مساعدتك اليوم؟")
            
            user_msg = Message(conversation_id=conversation_id, role="user", content=user_query, language="ar" if is_ar else "en")
            db.add(user_msg)
            db.commit()

            assistant_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_text,
                language="ar" if is_ar else "en",
                provider="internal",
                model="conversational-intent-gate",
                latency_ms=latency,
                cost_usd=0.0
            )
            db.add(assistant_msg)

            usage = UsageLog(
                conversation_id=conversation_id,
                provider="internal",
                model="intent-gate",
                capability="llm",
                latency_ms=latency,
                cost_usd=0.0,
                status="success"
            )
            db.add(usage)
            db.commit()
            db.refresh(assistant_msg)

            return {
                "message_id": assistant_msg.id,
                "role": "assistant",
                "content": assistant_text,
                "citations": [],
                "provider": "internal",
                "model": "intent-gate",
                "latency_ms": latency,
                "cost_usd": 0.0,
                "is_conversational": True,
                "is_fallback": False,
                "fallback_info": None
            }

        # 2. Knowledge Retrieval (STRICT SCOPE: strictly only if kb_id is provided)
        retrieved_chunks: List[RetrievedChunk] = []
        if kb_id:
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

            retrieved_chunks = self.retrieval_svc.hybrid_search(
                kb_id=kb_id,
                query=user_query,
                all_chunks=chunk_dicts,
                top_k=min(settings_dto.top_k, 3) if is_voice else settings_dto.top_k,
                hybrid_alpha=settings_dto.hybrid_alpha,
                similarity_threshold=settings_dto.similarity_threshold,
                reranker_enabled=settings_dto.reranker_enabled
            )

            # Abstention check
            if not retrieved_chunks and settings_dto.abstention_enabled and len(chunk_dicts) > 0:
                abstain_text = (
                    "لم أتمكن من العثور على معلومات كافية في قاعدة المعرفة المحددة للإجابة على استفسارك بدقة."
                    if is_ar
                    else "I could not find relevant information in the provided knowledge base to answer this question."
                )
                latency = round((time.perf_counter() - start_time) * 1000, 2)

                user_msg = Message(conversation_id=conversation_id, role="user", content=user_query, language="ar" if is_ar else "en")
                db.add(user_msg)
                db.commit()

                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=abstain_text,
                    language="ar" if is_ar else "en",
                    provider="retrieval",
                    model="abstention-gate",
                    latency_ms=latency,
                    cost_usd=0.0
                )
                db.add(assistant_msg)
                db.commit()
                db.refresh(assistant_msg)

                return {
                    "message_id": assistant_msg.id,
                    "role": "assistant",
                    "content": abstain_text,
                    "citations": [],
                    "provider": "retrieval",
                    "model": "abstention-gate",
                    "latency_ms": latency,
                    "cost_usd": 0.0,
                    "abstained": True,
                    "is_fallback": False,
                    "fallback_info": None
                }

        # 3. Model Selection via Smart Router
        provider_name, model_name = self.router.select_model(
            settings=settings_dto,
            intent=intent,
            query_token_estimate=len(user_query.split()),
            has_docs=bool(retrieved_chunks),
            is_voice=is_voice
        )
        adapter = get_provider_adapter(provider_name)
        if not adapter:
            provider_name = "openai"
            model_name = "gpt-4o-mini"
            adapter = get_provider_adapter("openai")

        # 4. Construct Grounded Prompt
        system_prompt = settings_dto.system_prompt_ar if is_ar else settings_dto.system_prompt_en
        context_blocks = []
        for idx, rc in enumerate(retrieved_chunks, start=1):
            page_info = f" (Page {rc.page_number})" if rc.page_number else ""
            context_blocks.append(f"[{idx}] Source: {rc.document_title}{page_info}\n{rc.content}")

        context_str = "\n\n".join(context_blocks)
        if retrieved_chunks:
            grounding_instruction = (
                f"\n\n--- KNOWLEDGE SOURCES ---\n{context_str}\n\n"
                "INSTRUCTIONS:\n"
                "1. Answer using ONLY the knowledge sources above.\n"
                "2. When stating facts, cite the source number using bracket notation like [1] or [2].\n"
                "3. If the knowledge sources do not contain the answer, say so clearly."
            )
            if is_ar:
                grounding_instruction += "\n4. The user asked in Arabic; write your response entirely in natural, fluent Arabic (العربية), translating facts from English sources accurately into Arabic."
            else:
                grounding_instruction += "\n4. The user's current message is in English. You MUST respond strictly in English, even if earlier messages in the conversation history were in Arabic."
            full_system_prompt = system_prompt + grounding_instruction
        else:
            full_system_prompt = system_prompt
            if not is_ar:
                full_system_prompt += "\n\nINSTRUCTION: The user's current message is in English. You MUST respond strictly in English, even if earlier messages in the conversation history were in Arabic."

        if is_voice:
            if is_ar:
                voice_prompt_instruction = (
                    "\n\nCRITICAL VOICE INSTRUCTION: Start your response with a very short, direct 8-12 word first sentence in Arabic that answers the core question immediately, "
                    "followed by 1-2 brief conversational spoken sentences in Arabic. Do NOT include citation numbers, bracket numbers like [1] or [2], markdown bolding, bullet points, or symbols."
                )
            else:
                voice_prompt_instruction = (
                    "\n\nCRITICAL VOICE INSTRUCTION: Start your response with a very short, direct 8-12 word first sentence that answers the core question immediately, "
                    "followed by 1-2 brief conversational spoken sentences. Do NOT include citation numbers, bracket numbers like [1] or [2], markdown bolding, bullet points, or symbols."
                )
            full_system_prompt = full_system_prompt + voice_prompt_instruction

        messages = [
            {"role": "system", "content": full_system_prompt},
            {"role": "user", "content": user_query}
        ]

        # 5. Call Provider Adapter with Fallback Tracking
        error_msg = None
        assistant_content = ""
        prompt_tokens = 0
        completion_tokens = 0
        is_fallback = False
        fallback_info = None

        try:
            res = await adapter.chat_complete(
                messages=messages,
                model=model_name,
                temperature=settings_dto.temperature,
                max_tokens=settings_dto.max_tokens,
                stream=False,
                is_voice=is_voice
            )
            self.router.report_success(provider_name)

            if "choices" in res and len(res["choices"]) > 0:
                assistant_content = res["choices"][0]["message"]["content"]
            elif "candidates" in res and len(res["candidates"]) > 0:
                candidate = res["candidates"][0]
                assistant_content = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
            else:
                assistant_content = str(res)

            usage_info = res.get("usage", {})
            prompt_tokens = usage_info.get("prompt_tokens", len(full_system_prompt.split()) + len(user_query.split()))
            completion_tokens = usage_info.get("completion_tokens", len(assistant_content.split()))

        except Exception as e:
            self.router.report_failure(provider_name)
            error_msg = str(e)
            
            # Circuit breaker fallback
            if settings_dto.fallback_enabled and settings_dto.fallback_provider and settings_dto.fallback_model:
                try:
                    fb_adapter = get_provider_adapter(settings_dto.fallback_provider)
                    if fb_adapter:
                        orig_prov, orig_mod = provider_name, model_name
                        provider_name = settings_dto.fallback_provider
                        model_name = settings_dto.fallback_model
                        res = await fb_adapter.chat_complete(
                            messages=messages,
                            model=model_name,
                            temperature=settings_dto.temperature,
                            max_tokens=settings_dto.max_tokens,
                            stream=False,
                            is_voice=is_voice
                        )
                        assistant_content = res["choices"][0]["message"]["content"]
                        error_msg = None
                        is_fallback = True
                        fallback_info = f"Requested provider {orig_prov} ({orig_mod}) was unavailable. Routed via fallback {provider_name} ({model_name})."
                except Exception as fb_err:
                    error_msg = f"Primary ({orig_prov}) and Fallback failed: {str(fb_err)}"
            
            if error_msg:
                assistant_content = f"Error generating response from {provider_name}: {error_msg}"

        latency = round((time.perf_counter() - start_time) * 1000, 2)
        cost_usd = self.pricing_calc.calculate_llm_cost(
            model=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )

        # 6. Save Messages
        user_msg = Message(conversation_id=conversation_id, role="user", content=user_query, language="ar" if is_ar else "en")
        db.add(user_msg)
        db.commit()

        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
            language="ar" if is_ar else "en",
            provider=provider_name,
            model=model_name,
            latency_ms=latency,
            cost_usd=cost_usd,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        # 7. Grounded Citations Filtering (Only attach chunks actually cited by LLM)
        citations_data = self._filter_grounded_citations(
            retrieved_chunks=retrieved_chunks,
            assistant_content=assistant_content,
            assistant_msg_id=assistant_msg.id,
            db=db
        )

        # 8. Record Usage
        usage = UsageLog(
            conversation_id=conversation_id,
            provider=provider_name,
            model=model_name,
            capability="llm",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost_usd,
            latency_ms=latency,
            status="error" if error_msg else "success",
            error_message=error_msg
        )
        db.add(usage)
        db.commit()

        return {
            "message_id": assistant_msg.id,
            "role": "assistant",
            "content": assistant_content,
            "citations": citations_data,
            "provider": provider_name,
            "model": model_name,
            "latency_ms": latency,
            "cost_usd": cost_usd,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "is_fallback": is_fallback,
            "fallback_info": fallback_info
        }

    async def answer_query_stream(
        self,
        db: Session,
        conversation_id: str,
        user_query: str,
        kb_id: Optional[str] = None,
        language: Optional[str] = None,
        use_rag: bool = True,
        is_voice: bool = False
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Server-Sent Events streaming query answering: yields real-time token deltas and final metadata.
        """
        # Strict scope isolation: if use_rag is False or kb_id is empty/null, strictly skip retrieval
        if not use_rag or kb_id in (None, "", "null", "none", "None"):
            kb_id = None

        start_time = time.perf_counter()
        t_db_start = time.perf_counter()
        settings_model = self.get_or_create_settings(db)
        settings_dto = AISettingsResponse.model_validate(settings_model)
        db_ms = round((time.perf_counter() - t_db_start) * 1000, 2)

        t_intent_start = time.perf_counter()
        # Script-first language detection:
        if re.search(r"[\u0600-\u06FF]", user_query):
            is_ar = True
        elif re.search(r"[A-Za-z]", user_query):
            is_ar = False
        else:
            is_ar = bool(language and language.lower().startswith("ar"))
        intent, canned_response = self.intent_classifier.classify(user_query)
        intent_ms = round((time.perf_counter() - t_intent_start) * 1000, 2)

        # 1. Pure Conversational Intent
        if intent == UserIntent.CONVERSATIONAL and not kb_id:
            assistant_text = canned_response or ("Hello! How can I assist you today?" if not is_ar else "مرحباً! كيف أستطيع مساعدتك اليوم؟")
            latency = round((time.perf_counter() - start_time) * 1000, 2)

            user_msg = Message(conversation_id=conversation_id, role="user", content=user_query, language="ar" if is_ar else "en")
            db.add(user_msg)
            db.commit()

            assistant_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_text,
                language="ar" if is_ar else "en",
                provider="internal",
                model="intent-gate",
                latency_ms=latency,
                cost_usd=0.0
            )
            db.add(assistant_msg)
            db.commit()
            db.refresh(assistant_msg)

            # Stream words with slight delay for smooth UI feedback
            words = assistant_text.split(" ")
            for w in words:
                yield {"type": "token", "data": {"token": w + " "}}

            yield {
                "type": "done",
                "data": {
                    "message_id": assistant_msg.id,
                    "content": assistant_text,
                    "citations": [],
                    "provider": "internal",
                    "model": "intent-gate",
                    "latency_ms": latency,
                    "cost_usd": 0.0,
                    "is_fallback": False,
                    "fallback_info": None
                }
            }
            return

        # 2. Knowledge Retrieval (STRICT SCOPE)
        retrieved_chunks: List[RetrievedChunk] = []
        if kb_id:
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

            t_ret_start = time.perf_counter()
            retrieved_chunks = self.retrieval_svc.hybrid_search(
                kb_id=kb_id,
                query=user_query,
                all_chunks=chunk_dicts,
                top_k=min(settings_dto.top_k, 3) if is_voice else settings_dto.top_k,
                hybrid_alpha=settings_dto.hybrid_alpha,
                similarity_threshold=settings_dto.similarity_threshold,
                reranker_enabled=settings_dto.reranker_enabled
            )
            ret_latency_ms = round((time.perf_counter() - t_ret_start) * 1000, 2)
            yield {
                "type": "retrieval",
                "data": {
                    "count": len(retrieved_chunks),
                    "latency_ms": ret_latency_ms
                }
            }

            # Abstention Check
            if not retrieved_chunks and settings_dto.abstention_enabled and len(chunk_dicts) > 0:
                abstain_text = (
                    "لم أتمكن من العثور على معلومات كافية في قاعدة المعرفة للإجابة على استفسارك بدقة."
                    if is_ar
                    else "I could not find relevant information in the provided knowledge base to answer this question."
                )
                latency = round((time.perf_counter() - start_time) * 1000, 2)

                user_msg = Message(conversation_id=conversation_id, role="user", content=user_query, language="ar" if is_ar else "en")
                db.add(user_msg)
                db.commit()

                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=abstain_text,
                    language="ar" if is_ar else "en",
                    provider="retrieval",
                    model="abstention-gate",
                    latency_ms=latency,
                    cost_usd=0.0
                )
                db.add(assistant_msg)
                db.commit()
                db.refresh(assistant_msg)

                yield {"type": "token", "data": {"token": abstain_text}}
                yield {
                    "type": "done",
                    "data": {
                        "message_id": assistant_msg.id,
                        "content": abstain_text,
                        "citations": [],
                        "provider": "retrieval",
                        "model": "abstention-gate",
                        "latency_ms": latency,
                        "cost_usd": 0.0,
                        "abstained": True,
                        "is_fallback": False,
                        "fallback_info": None
                    }
                }
                return

        # 3. Model Selection
        t_router_start = time.perf_counter()
        provider_name, model_name = self.router.select_model(
            settings=settings_dto,
            intent=intent,
            query_token_estimate=len(user_query.split()),
            has_docs=bool(retrieved_chunks),
            is_voice=is_voice
        )
        router_ms = round((time.perf_counter() - t_router_start) * 1000, 2)
        adapter = get_provider_adapter(provider_name)
        if not adapter:
            provider_name = "openai"
            model_name = "gpt-4o-mini"
            adapter = get_provider_adapter("openai")

        # 4. Prompt Construction
        system_prompt = settings_dto.system_prompt_ar if is_ar else settings_dto.system_prompt_en
        context_blocks = []
        for idx, rc in enumerate(retrieved_chunks, start=1):
            page_info = f" (Page {rc.page_number})" if rc.page_number else ""
            context_blocks.append(f"[{idx}] Source: {rc.document_title}{page_info}\n{rc.content}")

        context_str = "\n\n".join(context_blocks)
        if retrieved_chunks:
            grounding_instruction = (
                f"\n\n--- KNOWLEDGE SOURCES ---\n{context_str}\n\n"
                "INSTRUCTIONS:\n"
                "1. Answer using ONLY the knowledge sources above.\n"
                "2. When stating facts, cite the source number using bracket notation like [1] or [2].\n"
                "3. If the knowledge sources do not contain the answer, say so clearly."
            )
            if is_ar:
                grounding_instruction += "\n4. The user asked in Arabic; write your response entirely in natural, fluent Arabic (العربية), translating facts from English sources accurately into Arabic."
            else:
                grounding_instruction += "\n4. The user's current message is in English. You MUST respond strictly in English, even if earlier messages in the conversation history were in Arabic."
            full_system_prompt = system_prompt + grounding_instruction
        else:
            full_system_prompt = system_prompt
            if not is_ar:
                full_system_prompt += "\n\nINSTRUCTION: The user's current message is in English. You MUST respond strictly in English, even if earlier messages in the conversation history were in Arabic."

        if is_voice:
            if is_ar:
                voice_prompt_instruction = (
                    "\n\nCRITICAL VOICE INSTRUCTION: Start your response with a very short, direct 8-12 word first sentence in Arabic that answers the core question immediately, "
                    "followed by 1-2 brief conversational spoken sentences in Arabic. Do NOT include citation numbers, bracket numbers like [1] or [2], markdown bolding, bullet points, or symbols."
                )
            else:
                voice_prompt_instruction = (
                    "\n\nCRITICAL VOICE INSTRUCTION: Start your response with a very short, direct 8-12 word first sentence that answers the core question immediately, "
                    "followed by 1-2 brief conversational spoken sentences. Do NOT include citation numbers, bracket numbers like [1] or [2], markdown bolding, bullet points, or symbols."
                )
            full_system_prompt = full_system_prompt + voice_prompt_instruction

        messages = [
            {"role": "system", "content": full_system_prompt},
            {"role": "user", "content": user_query}
        ]

        # 5. Execute Streaming from Provider Adapter
        is_fallback = False
        fallback_info = None
        full_assistant_text = ""
        stream_iter = None
        first_token = None

        async def create_stream(p_name: str, m_name: str):
            p_adapter = get_provider_adapter(p_name)
            if not p_adapter:
                raise ValueError(f"Adapter for provider '{p_name}' not available")
            return await p_adapter.chat_complete(
                messages=messages,
                model=m_name,
                temperature=settings_dto.temperature,
                max_tokens=settings_dto.max_tokens,
                stream=True,
                is_voice=is_voice
            )

        # Attempt primary provider
        primary_failed = False
        primary_error_msg = ""
        t_stream_start = time.perf_counter()
        try:
            stream_gen = await create_stream(provider_name, model_name)
            stream_iter = aiter(stream_gen)
            # Try obtaining first token to verify stream is functional (catches 4xx/5xx on first iteration)
            first_token = await anext(stream_iter)
            self.router.report_success(provider_name)
        except (StopAsyncIteration, Exception) as e:
            primary_failed = True
            primary_error_msg = str(e) or "Empty stream on first token"
            self.router.report_failure(provider_name)

        # Fallback handling if primary failed before first token
        if primary_failed:
            if settings_dto.fallback_enabled and settings_dto.fallback_provider and settings_dto.fallback_model:
                orig_p, orig_m = provider_name, model_name
                provider_name = settings_dto.fallback_provider
                model_name = settings_dto.fallback_model
                is_fallback = True
                fallback_info = f"Requested provider {orig_p} ({orig_m}) was unavailable ({primary_error_msg}). Routed via fallback {provider_name} ({model_name})."
                try:
                    fb_stream_gen = await create_stream(provider_name, model_name)
                    stream_iter = aiter(fb_stream_gen)
                    first_token = await anext(stream_iter)
                    self.router.report_success(provider_name)
                    primary_failed = False
                except Exception as fb_err:
                    self.router.report_failure(provider_name)
                    # DO NOT save or yield an empty content: "" bubble
                    yield {"type": "error", "data": {"message": f"Primary ({orig_p}) and fallback ({provider_name}) failed: {str(fb_err)}"}}
                    return
            else:
                # Fallback disabled, primary failed
                # DO NOT save or yield an empty content: "" bubble
                yield {"type": "error", "data": {"message": f"Provider {provider_name} failed: {primary_error_msg}"}}
                return

        # Stage timings instrumentation
        llm_ttft_ms = round((time.perf_counter() - t_stream_start) * 1000, 2)
        total_pre_ttft_ms = round((time.perf_counter() - start_time) * 1000, 2)
        stage_timings = {
            "db_read_ms": db_ms,
            "intent_classification_ms": intent_ms,
            "retrieval_ms": ret_latency_ms if kb_id else 0.0,
            "router_selection_ms": router_ms,
            "llm_first_token_ms": llm_ttft_ms,
            "total_pre_ttft_ms": total_pre_ttft_ms
        }
        yield {"type": "stage_timings", "data": stage_timings}

        # Emit the first token
        if first_token is not None:
            full_assistant_text += first_token
            yield {"type": "token", "data": {"token": first_token}}

        # Stream remaining tokens
        try:
            async for delta in stream_iter:
                full_assistant_text += delta
                yield {"type": "token", "data": {"token": delta}}
        except Exception as stream_err:
            yield {"type": "token", "data": {"token": f"\n[Stream interrupted: {str(stream_err)}]"}}

        # If empty response, do NOT save or yield empty bubble
        if not full_assistant_text.strip():
            yield {"type": "error", "data": {"message": "Empty response received from provider."}}
            return

        latency = round((time.perf_counter() - start_time) * 1000, 2)
        prompt_tokens = len(full_system_prompt.split()) + len(user_query.split())
        completion_tokens = len(full_assistant_text.split())
        cost_usd = self.pricing_calc.calculate_llm_cost(model=model_name, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)

        # 6. Save in DB
        user_msg = Message(conversation_id=conversation_id, role="user", content=user_query, language="ar" if is_ar else "en")
        db.add(user_msg)
        db.commit()

        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_assistant_text,
            language="ar" if is_ar else "en",
            provider=provider_name,
            model=model_name,
            latency_ms=latency,
            cost_usd=cost_usd,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        # 7. Grounded Citations Filtering
        citations_data = self._filter_grounded_citations(
            retrieved_chunks=retrieved_chunks,
            assistant_content=full_assistant_text,
            assistant_msg_id=assistant_msg.id,
            db=db
        )

        # 8. Record Usage
        usage = UsageLog(
            conversation_id=conversation_id,
            provider=provider_name,
            model=model_name,
            capability="llm",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost_usd,
            latency_ms=latency,
            status="success"
        )
        db.add(usage)
        db.commit()

        yield {
            "type": "done",
            "data": {
                "message_id": assistant_msg.id,
                "content": full_assistant_text,
                "citations": citations_data,
                "provider": provider_name,
                "model": model_name,
                "latency_ms": latency,
                "cost_usd": cost_usd,
                "is_fallback": is_fallback,
                "fallback_info": fallback_info
            }
        }

_RAG_SERVICE = RAGService()

def get_rag_service() -> RAGService:
    return _RAG_SERVICE
