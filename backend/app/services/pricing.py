from typing import Dict, Any, Optional

# Standard prices per million tokens (USD)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-2024-08-06": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "gpt-4o-realtime-preview": {"input": 5.00, "output": 20.00},
    
    # Gemini
    "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash-exp": {"input": 0.00, "output": 0.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    
    # CheaperInference default
    "cheaper-default": {"input": 0.10, "output": 0.20},
}

# STT cost per second in USD
STT_PRICING_PER_SEC: Dict[str, float] = {
    "whisper-1": 0.006 / 60.0, # $0.006 per minute
}

# TTS cost per 1000 characters in USD
TTS_PRICING_PER_1K_CHARS: Dict[str, float] = {
    "tts-1": 0.015,
    "tts-1-hd": 0.030,
    "edge_tts": 0.00, # Free
}

class PricingCalculator:
    @staticmethod
    def calculate_llm_cost(
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        custom_input_cost_1m: Optional[float] = None,
        custom_output_cost_1m: Optional[float] = None
    ) -> float:
        """Calculates total cost in USD for LLM invocation."""
        if custom_input_cost_1m is not None and custom_output_cost_1m is not None:
            in_rate = custom_input_cost_1m / 1_000_000.0
            out_rate = custom_output_cost_1m / 1_000_000.0
        else:
            rates = MODEL_PRICING.get(model.lower())
            if not rates:
                # Fuzzy match
                for k, v in MODEL_PRICING.items():
                    if k in model.lower():
                        rates = v
                        break
            if not rates:
                rates = {"input": 0.50, "output": 1.50} # Conservative fallback
            
            in_rate = rates["input"] / 1_000_000.0
            out_rate = rates["output"] / 1_000_000.0

        total = (prompt_tokens * in_rate) + (completion_tokens * out_rate)
        return round(total, 6)

    @staticmethod
    def calculate_stt_cost(model: str, audio_duration_seconds: float) -> float:
        rate = STT_PRICING_PER_SEC.get(model, 0.0001)
        return round(audio_duration_seconds * rate, 6)

    @staticmethod
    def calculate_tts_cost(provider: str, model_or_voice: str, char_count: int) -> float:
        if provider == "edge_tts":
            return 0.0
        rate = TTS_PRICING_PER_1K_CHARS.get(model_or_voice, 0.015)
        return round((char_count / 1000.0) * rate, 6)

_PRICING_CALCULATOR = PricingCalculator()

def get_pricing_calculator() -> PricingCalculator:
    return _PRICING_CALCULATOR

