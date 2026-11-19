from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_list_providers():
    res = client.get("/api/v1/providers")
    assert res.status_code == 200
    providers = res.json()
    p_ids = [p["provider"] for p in providers]
    assert "openai" in p_ids
    assert "gemini" in p_ids
    assert "openrouter" in p_ids
    assert "cheaper_inference" in p_ids
    assert "edge_tts" in p_ids

def test_list_voices_edge_tts():
    res = client.get("/api/v1/providers/edge_tts/voices")
    assert res.status_code == 200
    voices = res.json()
    assert len(voices) >= 5
    # Verify Arabic and English voices exist
    ar_voices = [v for v in voices if "ar" in v["language"]]
    en_voices = [v for v in voices if "en" in v["language"]]
    assert len(ar_voices) > 0
    assert len(en_voices) > 0

def test_get_and_update_settings():
    # 1. Get settings
    get_res = client.get("/api/v1/settings")
    assert get_res.status_code == 200
    settings = get_res.json()
    assert "llm_provider" in settings
    assert "routing_strategy" in settings

    # 2. Update settings
    put_res = client.put("/api/v1/settings", json={
        "routing_strategy": "balanced",
        "temperature": 0.5,
        "abstention_enabled": True
    })
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["routing_strategy"] == "balanced"
    assert updated["temperature"] == 0.5
    assert updated["abstention_enabled"] is True

def test_analytics_summary():
    res = client.get("/api/v1/analytics/summary")
    assert res.status_code == 200
    summary = res.json()
    assert "total_requests" in summary
    assert "total_tokens" in summary
    assert "total_cost_usd" in summary
