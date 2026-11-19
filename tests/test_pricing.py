from backend.app.services.pricing import PricingCalculator

def test_llm_cost_calculation():
    calc = PricingCalculator()
    
    # gpt-4o-mini ($0.15 / $0.60 per 1M)
    # 1,000 prompt tokens = $0.00015
    # 500 completion tokens = $0.00030
    cost_mini = calc.calculate_llm_cost("gpt-4o-mini", prompt_tokens=1000, completion_tokens=500)
    assert cost_mini == 0.00045

    # gemini-2.0-flash ($0.075 / $0.30 per 1M)
    cost_flash = calc.calculate_llm_cost("gemini-2.0-flash", prompt_tokens=1000, completion_tokens=1000)
    assert cost_flash == 0.000375

def test_stt_cost_calculation():
    calc = PricingCalculator()
    # 60 seconds of whisper = $0.006
    cost_stt = calc.calculate_stt_cost("whisper-1", audio_duration_seconds=60.0)
    assert abs(cost_stt - 0.006) < 0.00001

def test_tts_cost_calculation():
    calc = PricingCalculator()
    # Edge TTS is free ($0.00)
    cost_edge = calc.calculate_tts_cost("edge_tts", "ar-SA-HamedNeural", 1000)
    assert cost_edge == 0.0

    # OpenAI TTS-1 ($0.015 per 1,000 chars)
    cost_openai = calc.calculate_tts_cost("openai", "tts-1", 1000)
    assert cost_openai == 0.015

