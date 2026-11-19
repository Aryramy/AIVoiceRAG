from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_conversation_lifecycle():
    # 1. Create conversation
    create_res = client.post("/api/v1/conversations", json={"title": "Test Chat", "language": "en"})
    assert create_res.status_code == 200
    conv_data = create_res.json()
    conv_id = conv_data["id"]
    assert conv_data["title"] == "Test Chat"

    # 2. List conversations
    list_res = client.get("/api/v1/conversations")
    assert list_res.status_code == 200
    items = list_res.json()
    assert any(c["id"] == conv_id for c in items)

    # 3. Post a conversational message (handled by intent gate)
    msg_res = client.post(f"/api/v1/conversations/{conv_id}/messages", json={
        "content": "Hello! How are you doing today?",
        "language": "en"
    })
    assert msg_res.status_code == 200
    msg_data = msg_res.json()
    assert msg_data["role"] == "assistant"
    assert "content" in msg_data
    assert len(msg_data["content"]) > 0

    # 4. Get conversation details
    detail_res = client.get(f"/api/v1/conversations/{conv_id}")
    assert detail_res.status_code == 200
    details = detail_res.json()
    assert len(details["messages"]) >= 2  # user + assistant

    # 5. Delete conversation
    del_res = client.delete(f"/api/v1/conversations/{conv_id}")
    assert del_res.status_code == 200

    # Verify deleted
    get_res = client.get(f"/api/v1/conversations/{conv_id}")
    assert get_res.status_code == 404
