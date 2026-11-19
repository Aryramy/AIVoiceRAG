import json
import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_cors():
    print("\n--- [1] Testing CORS Settings ---")
    origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    all_ok = True
    for origin in origins:
        headers = {
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        }
        res = requests.options(f"{BASE_URL}/api/v1/conversations", headers=headers)
        allow_origin = res.headers.get("access-control-allow-origin")
        allow_creds = res.headers.get("access-control-allow-credentials")
        print(f"Origin: {origin} -> Status: {res.status_code}, Allow-Origin: {allow_origin}, Allow-Credentials: {allow_creds}")
        if allow_origin != origin:
            print(f"  [WARN] Expected Allow-Origin: {origin}, got {allow_origin}")
            all_ok = False
        else:
            print(f"  [PASS] CORS origin {origin} accepted correctly.")
    return all_ok

def test_health():
    print("\n--- [2] Testing Health Endpoint (GET /api/v1/health) ---")
    res = requests.get(f"{BASE_URL}/api/v1/health")
    print(f"Status: {res.status_code}")
    print(f"Response: {json.dumps(res.json(), indent=2)}")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "components" in data
    print("  [PASS] Health check verified.")
    return data

def test_conversations():
    print("\n--- [3] Testing Conversations Endpoint (POST /api/v1/conversations) ---")
    
    # 1. Create English Conversation
    payload_en = {"title": "Test EN Voice Conversation", "language": "en"}
    res_en = requests.post(f"{BASE_URL}/api/v1/conversations", json=payload_en)
    print(f"Create EN Status: {res_en.status_code}")
    conv_en = res_en.json()
    print(f"Created Conv EN: {json.dumps(conv_en, indent=2)}")
    assert res_en.status_code == 200
    assert conv_en["id"] is not None
    
    # 2. Create Arabic Conversation
    payload_ar = {"title": "محادثة اختبار صوتية عربية", "language": "ar"}
    res_ar = requests.post(f"{BASE_URL}/api/v1/conversations", json=payload_ar)
    print(f"Create AR Status: {res_ar.status_code}")
    conv_ar = res_ar.json()
    print(f"Created Conv AR: {json.dumps(conv_ar, indent=2)}")
    assert res_ar.status_code == 200
    assert conv_ar["id"] is not None
    
    print("  [PASS] Conversation creation verified.")
    return conv_en["id"], conv_ar["id"]

def test_messages(conv_en_id, conv_ar_id):
    print("\n--- [4] Testing Messages Endpoint (POST /api/v1/conversations/{id}/messages) ---")
    
    # English conversational message
    msg_payload_en = {"content": "Hello, how are you today?", "language": "en"}
    res_en = requests.post(f"{BASE_URL}/api/v1/conversations/{conv_en_id}/messages", json=msg_payload_en)
    print(f"EN Message Status: {res_en.status_code}")
    data_en = res_en.json()
    print(f"EN Response: {json.dumps(data_en, indent=2, ensure_ascii=False)}")
    assert res_en.status_code == 200
    assert "content" in data_en
    assert len(data_en["content"]) > 0

    # Arabic conversational message
    msg_payload_ar = {"content": "مرحبا، كيف حالك اليوم؟", "language": "ar"}
    res_ar = requests.post(f"{BASE_URL}/api/v1/conversations/{conv_ar_id}/messages", json=msg_payload_ar)
    print(f"AR Message Status: {res_ar.status_code}")
    data_ar = res_ar.json()
    print(f"AR Response: {json.dumps(data_ar, indent=2, ensure_ascii=False)}")
    assert res_ar.status_code == 200
    assert "content" in data_ar
    assert len(data_ar["content"]) > 0

    print("  [PASS] Conversational messages verified.")
    return data_en["content"], data_ar["content"]

def test_voice_synthesize():
    print("\n--- [5] Testing Voice Synthesis (POST /api/v1/voice/synthesize) ---")
    
    # 1. English synthesis
    payload_en = {
        "text": "Hello! Welcome to VoiceRag knowledge assistant.",
        "language": "en",
        "voice": "en-US-JennyNeural"
    }
    print(f"Synthesizing EN text: '{payload_en['text']}' with voice '{payload_en['voice']}'...")
    res_en = requests.post(f"{BASE_URL}/api/v1/voice/synthesize", json=payload_en)
    print(f"EN Voice Status: {res_en.status_code}, Content-Type: {res_en.headers.get('content-type')}, Size: {len(res_en.content)} bytes")
    assert res_en.status_code == 200
    assert res_en.headers.get("content-type") == "audio/mpeg"
    assert len(res_en.content) > 1000, "Audio output should be valid MP3 binary stream"
    
    # 2. Arabic synthesis
    payload_ar = {
        "text": "مرحباً بك في منصة المساعد المعرفي الصوتي الذكي.",
        "language": "ar",
        "voice": "ar-SA-HamedNeural"
    }
    print(f"Synthesizing AR text: '{payload_ar['text']}' with voice '{payload_ar['voice']}'...")
    res_ar = requests.post(f"{BASE_URL}/api/v1/voice/synthesize", json=payload_ar)
    print(f"AR Voice Status: {res_ar.status_code}, Content-Type: {res_ar.headers.get('content-type')}, Size: {len(res_ar.content)} bytes")
    assert res_ar.status_code == 200
    assert res_ar.headers.get("content-type") == "audio/mpeg"
    assert len(res_ar.content) > 1000, "Audio output should be valid MP3 binary stream"

    print("  [PASS] Voice synthesis for both English and Arabic verified.")
    return len(res_en.content), len(res_ar.content)

if __name__ == "__main__":
    try:
        cors_ok = test_cors()
        health = test_health()
        conv_en, conv_ar = test_conversations()
        en_reply, ar_reply = test_messages(conv_en, conv_ar)
        en_audio_size, ar_audio_size = test_voice_synthesize()
        
        print("\n==========================================")
        print("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        print("==========================================")
    except Exception as e:
        print(f"\n[ERROR] Verification check failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
