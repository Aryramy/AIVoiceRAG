import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.integrations.cheaper_inference_adapter import CheaperInferenceAdapter, CHEAPER_INFERENCE_VOICES
from backend.app.integrations.openrouter_adapter import OpenRouterAdapter, OPENROUTER_VOICES
from backend.app.integrations.gemini_adapter import GeminiAdapter, GEMINI_STUDIO_VOICES
from backend.app.integrations.openai_adapter import OpenAIAdapter, OPENAI_NATIVE_VOICES
from backend.app.api.routes.providers import PROVIDERS_METADATA
from backend.app.services.router import get_router
from backend.app.schemas.settings import AISettingsResponse
from backend.app.services.intent import UserIntent
from backend.app.services.rag import get_rag_service

client = TestClient(app)

@pytest.mark.asyncio
async def test_cheaper_inference_adapter_categorization():
    adapter = CheaperInferenceAdapter(api_key="test-key")
    assert adapter.provider_name == "cheaper_inference"

    mock_models_response = {
        "data": [
            {"id": "text-model-1", "type": "text", "endpoint": "/v1/chat/completions", "context_length": 16384},
            {"id": "whisper-transcribe", "type": "transcription", "endpoint": "/v1/audio/transcriptions"},
            {"id": "speech-gen-1", "type": "speech", "endpoint": "/v1/audio/speech"},
            {"id": "custom-tts-model", "type": "other", "endpoint": "/v1/custom"},
        ]
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_models_response
        mock_get.return_value = mock_resp

        models = await adapter.list_models()
        assert len(models) == 4

        m_map = {m.id: m for m in models}
        assert "llm" in m_map["text-model-1"].capabilities
        assert "stt" in m_map["whisper-transcribe"].capabilities
        assert "tts" in m_map["speech-gen-1"].capabilities
        assert "tts" in m_map["custom-tts-model"].capabilities

    # Test voices
    voices = await adapter.list_voices()
    assert len(voices) == len(CHEAPER_INFERENCE_VOICES)
    assert len(voices) == 39
    voice_ids = [v.id for v in voices]
    assert "alloy" in voice_ids
    assert "rachel" in voice_ids
    assert "giggle" in voice_ids

@pytest.mark.asyncio
async def test_openrouter_adapter_categorization():
    adapter = OpenRouterAdapter(api_key="test-key")
    assert adapter.provider_name == "openrouter"

    mock_models_response = {
        "data": [
            {
                "id": "meta-llama/llama-3-8b",
                "name": "Llama 3 8B",
                "architecture": {"modality": "text->text"},
                "pricing": {"prompt": "0.0000001", "completion": "0.0000002"}
            },
            {
                "id": "openai/whisper-large-v3",
                "name": "Whisper Large",
                "architecture": {"modality": "audio->text"},
                "pricing": {"prompt": "0.0000001", "completion": "0.0000002"}
            },
            {
                "id": "openai/gpt-4o-audio-preview",
                "name": "GPT-4o Audio",
                "architecture": {"modality": "text+audio->text+audio"},
                "pricing": {"prompt": "0.000005", "completion": "0.000015"}
            }
        ]
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_models_response
        mock_get.return_value = mock_resp

        models = await adapter.list_models()
        assert len(models) == 3
        m_map = {m.id: m for m in models}
        assert "llm" in m_map["meta-llama/llama-3-8b"].capabilities
        assert "stt" in m_map["openai/whisper-large-v3"].capabilities
        assert "tts" in m_map["openai/gpt-4o-audio-preview"].capabilities

    # Test voices
    voices = await adapter.list_voices()
    assert len(voices) == len(OPENROUTER_VOICES)
    assert len(voices) == 6
    voice_ids = [v.id for v in voices]
    assert "alloy" in voice_ids
    assert "shimmer" in voice_ids

@pytest.mark.asyncio
async def test_gemini_adapter_categorization_and_voices():
    adapter = GeminiAdapter(api_key="test-key")
    assert adapter.provider_name == "gemini"

    mock_models_response = {
        "models": [
            {
                "name": "models/gemini-2.5-flash",
                "displayName": "Gemini 2.5 Flash",
                "supportedGenerationMethods": ["generateContent"]
            },
            {
                "name": "models/gemini-2.5-flash-preview-tts",
                "displayName": "Gemini 2.5 Flash Preview TTS",
                "supportedGenerationMethods": ["generateContent"]
            },
            {
                "name": "models/imagen-3.0",
                "displayName": "Imagen 3.0",
                "supportedGenerationMethods": ["generateImages"]
            }
        ]
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_models_response
        mock_get.return_value = mock_resp

        models = await adapter.list_models()
        assert len(models) == 2 # imagen filtered out because no generateContent
        m_map = {m.id: m for m in models}
        assert "llm" in m_map["gemini-2.5-flash"].capabilities
        assert "stt" in m_map["gemini-2.5-flash"].capabilities
        assert "tts" in m_map["gemini-2.5-flash-preview-tts"].capabilities

    # Test 30 studio voices
    voices = await adapter.list_voices()
    assert len(voices) == len(GEMINI_STUDIO_VOICES)
    assert len(voices) == 30
    voice_names = [v.name for v in voices]
    assert "Gemini Puck" in voice_names
    assert "Gemini Aoede" in voice_names
    assert "Gemini Gacrux" in voice_names

@pytest.mark.asyncio
async def test_openai_adapter_audio_models_and_voices():
    adapter = OpenAIAdapter(api_key="test-key")
    assert adapter.provider_name == "openai"

    mock_models_response = {
        "data": [
            {"id": "gpt-4o"},
            {"id": "gpt-4o-mini"},
        ]
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_models_response
        mock_get.return_value = mock_resp

        models = await adapter.list_models()
        m_map = {m.id: m for m in models}
        # Check LLMs
        assert "llm" in m_map["gpt-4o"].capabilities
        assert "llm" in m_map["gpt-4o-mini"].capabilities
        # Check injected STT and TTS models
        assert "whisper-1" in m_map
        assert "stt" in m_map["whisper-1"].capabilities
        assert "gpt-4o-transcribe" in m_map
        assert "stt" in m_map["gpt-4o-transcribe"].capabilities
        assert "tts-1" in m_map
        assert "tts" in m_map["tts-1"].capabilities
        assert "tts-1-hd" in m_map
        assert "tts" in m_map["tts-1-hd"].capabilities

    # Test 11 native voices
    voices = await adapter.list_voices()
    assert len(voices) == len(OPENAI_NATIVE_VOICES)
    assert len(voices) == 11
    voice_ids = [v.id for v in voices]
    assert "alloy" in voice_ids
    assert "verse" in voice_ids
    assert "ballad" in voice_ids

def test_providers_metadata_and_route():
    for p in ["openai", "gemini", "openrouter", "cheaper_inference"]:
        assert PROVIDERS_METADATA[p]["capabilities"] == ["llm", "stt", "tts"]
    assert PROVIDERS_METADATA["edge_tts"]["capabilities"] == ["tts"]

    res = client.get("/api/v1/providers")
    assert res.status_code == 200
    p_list = res.json()
    p_dict = {p["provider"]: p for p in p_list}
    for p in ["openai", "gemini", "openrouter", "cheaper_inference"]:
        assert p_dict[p]["supported_capabilities"] == ["llm", "stt", "tts"]

def test_router_gemini_2_5_flash():
    router = get_router()
    settings = AISettingsResponse(
        routing_strategy="low_cost",
        llm_provider="gemini",
        llm_model="gemini-2.5-flash",
        top_k=4,
        similarity_threshold=0.5,
        hybrid_alpha=0.5,
        reranker_enabled=False,
        abstention_enabled=False,
        temperature=0.7,
        max_tokens=2048,
        fallback_enabled=False,
        stt_provider="openai",
        tts_provider="edge_tts",
        tts_voice_en="en-US-JennyNeural",
        tts_voice_ar="ar-SA-HamedNeural",
        system_prompt_en="Helpful assistant",
        system_prompt_ar="مساعد مفيد"
    )

    prov, model = router.select_model(settings=settings, intent=UserIntent.KNOWLEDGE)
    assert prov == "gemini"
    assert model in ["gemini-flash-latest", "gemini-2.5-flash"]
    assert "gemini-2.0-flash" not in model

@pytest.mark.asyncio
async def test_rag_is_voice_injection():
    rag = get_rag_service()
    mock_adapter = AsyncMock()
    mock_adapter.chat_complete.return_value = {
        "choices": [{"message": {"content": "Spoken concise answer."}}]
    }

    with patch("backend.app.services.rag.get_provider_adapter", return_value=mock_adapter):
        from backend.app.core.database import SessionLocal
        from backend.app.database.models import Conversation
        db = SessionLocal()
        try:
            conv = db.query(Conversation).filter(Conversation.id == "test-conv-voice").first()
            if not conv:
                conv = Conversation(id="test-conv-voice", title="Voice Test")
                db.add(conv)
                db.commit()

            res = await rag.answer_query(
                db=db,
                conversation_id="test-conv-voice",
                user_query="Tell me about the sun",
                use_rag=False,
                is_voice=True
            )
            assert res["content"] == "Spoken concise answer."
            call_kwargs = mock_adapter.chat_complete.call_args[1]
            sys_msg = call_kwargs["messages"][0]["content"]
            assert "CRITICAL VOICE INSTRUCTION: Start your response with a very short, direct 8-12 word first sentence" in sys_msg
        finally:
            db.close()

@pytest.mark.asyncio
async def test_rag_stream_fallback_before_first_token():
    rag = get_rag_service()

    async def chat_complete_fail(*args, **kwargs):
        async def failing_gen():
            raise RuntimeError("Primary 503 Service Unavailable")
            yield "never"
        return failing_gen()

    async def chat_complete_fallback(*args, **kwargs):
        async def working_gen():
            yield "Fallback "
            yield "response."
        return working_gen()

    primary_adapter = MagicMock()
    primary_adapter.chat_complete = chat_complete_fail

    fallback_adapter = MagicMock()
    fallback_adapter.chat_complete = chat_complete_fallback

    def adapter_side_effect(name):
        if name == "openai":
            return primary_adapter
        elif name == "gemini":
            return fallback_adapter
        return None

    from backend.app.core.database import SessionLocal
    from backend.app.database.models import AISettings, Conversation, Message
    db = SessionLocal()
    try:
        conv = db.query(Conversation).filter(Conversation.id == "conv-fb-test").first()
        if not conv:
            conv = Conversation(id="conv-fb-test", title="Fallback Test")
            db.add(conv)
            db.commit()

        settings = db.query(AISettings).first()
        if not settings:
            settings = AISettings()
            db.add(settings)
        settings.llm_provider = "openai"
        settings.llm_model = "gpt-4o"
        settings.fallback_enabled = True
        settings.fallback_provider = "gemini"
        settings.fallback_model = "gemini-2.5-flash"
        db.commit()

        with patch("backend.app.services.rag.get_provider_adapter", side_effect=adapter_side_effect):
            events = []
            async for evt in rag.answer_query_stream(
                db=db,
                conversation_id="conv-fb-test",
                user_query="Tell me a joke",
                use_rag=False
            ):
                events.append(evt)

            tokens = [e["data"]["token"] for e in events if e["type"] == "token"]
            full_text = "".join(tokens)
            assert full_text == "Fallback response."

            done_evt = [e for e in events if e["type"] == "done"][0]
            assert done_evt["data"]["is_fallback"] is True
            assert done_evt["data"]["provider"] == "gemini"
            assert done_evt["data"]["content"] == "Fallback response."

            msg = db.query(Message).filter(Message.id == done_evt["data"]["message_id"]).first()
            assert msg is not None
            assert msg.content == "Fallback response."
    finally:
        db.close()

def test_voice_routes_dynamic():
    # 1. Edge TTS voices
    res = client.get("/api/v1/providers/edge_tts/voices")
    assert res.status_code == 200
    assert len(res.json()) > 0

    # 2. OpenAI voices
    res = client.get("/api/v1/providers/openai/voices")
    assert res.status_code == 200
    assert len(res.json()) == 11

    # 3. Gemini voices
    res = client.get("/api/v1/providers/gemini/voices")
    assert res.status_code == 200
    assert len(res.json()) == 30

    # 4. CheaperInference voices
    res = client.get("/api/v1/providers/cheaper_inference/voices")
    assert res.status_code == 200
    assert len(res.json()) == 39

    # 5. OpenRouter voices
    res = client.get("/api/v1/providers/openrouter/voices")
    assert res.status_code == 200
    assert len(res.json()) == 6
