import re
from typing import Tuple, Optional
from enum import Enum

class UserIntent(str, Enum):
    CONVERSATIONAL = "conversational"  # Greetings, thanks, small talk, pleasantries
    KNOWLEDGE = "knowledge"            # Document questions, queries, summaries, factual requests
    NOISE = "noise"                    # Environmental noise, audio cutoffs, unintelligible fragments

# Conversational expressions in English and Arabic
CONVERSATIONAL_PATTERNS_EN = [
    r"^(hi|hello|hey|howdy|greetings|good\s+(morning|afternoon|evening|day|night))\b",
    r"^(thank\s*you|thanks|thx|much\s+appreciated|appreciate\s+it)\b",
    r"^(great|awesome|excellent|cool|perfect|nice|wonderful|good\s+job|well\s+done)\b",
    r"^(how\s+are\s+you|how\s+is\s+it\s+going|what'?s\s+up|how\s+do\s+you\s+do)\b",
    r"^(goodbye|bye|see\s+you|cya|take\s+care|talk\s+to\s+you\s+later)\b",
    r"^(yes|no|okay|ok|sure|alright|fine|got\s+it|understood)\b",
    r"^(who\s+are\s+you|what\s+can\s+you\s+do|what\s+is\s+your\s+name)\b"
]

CONVERSATIONAL_PATTERNS_AR = [
    r"^(مرحبا|مرحباً|أهلا|أهلاً|السلام\s+عليكم|صباح\s+الخير|مساء\s+الخير)\b",
    r"^(شكرا|شكراً|مشكور|جزاك\s+الله\s+خيرا|يعطيك\s+العافية|تسلم)\b",
    r"^(ممتاز|رائع|جميل|عظيم|أحسنت|حسنا|حسناً|تمام|ماشي)\b",
    r"^(كيف\s+حالك|شخبارك|كيفك|كيف\s+الصحة|ما\s+أخبارك)\b",
    r"^(مع\s+السلامة|إلى\s+اللقاء|وداعا|وداعاً|باي|تصبح\s+على\s+خير)\b",
    r"^(نعم|لا|أجل|فهمت|واضح|بالتأكيد)\b",
    r"^(من\s+أنت|ما\s+اسمك|ماذا\s+تستطيع\s+أن\s+تفعل)\b"
]

CONVERSATIONAL_RESPONSES = {
    "greeting_en": "Hello! How can I assist you with your knowledge bases or questions today?",
    "greeting_ar": "مرحباً بك! كيف يمكنني مساعدتك اليوم في استعراض مستنداتك أو الإجابة على استفساراتك؟",
    "thanks_en": "You're very welcome! Let me know if you need any further insights or analysis.",
    "thanks_ar": "على الرحب والسعة! أنا هنا دائماً لمساعدتك في أي استفسار آخر.",
    "acknowledgement_en": "Glad to hear that. What would you like to explore next?",
    "acknowledgement_ar": "يسعدني ذلك كثيراً. ما الذي تود الاطلاع عليه بعد ذلك؟",
    "how_are_you_en": "I'm functioning smoothly and ready to assist you with your research, documents, or voice queries. How are you doing?",
    "how_are_you_ar": "أنا بأفضل حال وجاهز تماماً لمساعدتك في البحث الصوتي وتحليل مستنداتك. كيف حالك أنت اليوم؟",
    "goodbye_en": "Goodbye! Have a productive day ahead.",
    "goodbye_ar": "مع السلامة! أتمنى لك يوماً مثمراً وموفقاً."
}

class IntentClassifier:
    def __init__(self):
        self.compiled_en = [re.compile(p, re.IGNORECASE) for p in CONVERSATIONAL_PATTERNS_EN]
        self.compiled_ar = [re.compile(p, re.UNICODE) for p in CONVERSATIONAL_PATTERNS_AR]

    def is_arabic(self, text: str) -> bool:
        # Check if text contains Arabic Unicode range (0600-06FF)
        return bool(re.search(r"[\u0600-\u06FF]", text))

    def classify(self, query: str) -> Tuple[UserIntent, Optional[str]]:
        """
        Classifies user query into CONVERSATIONAL, KNOWLEDGE, or NOISE.
        Returns (UserIntent, natural_response_if_conversational)
        """
        cleaned = query.strip()
        
        # Noise check: extremely short unintelligible text or isolated punctuation
        if len(cleaned) <= 1 or re.match(r"^[\.\,\?\!\s\-_]+$", cleaned):
            return UserIntent.NOISE, None

        is_ar = self.is_arabic(cleaned)
        patterns = self.compiled_ar if is_ar else self.compiled_en

        for pattern in patterns:
            if pattern.search(cleaned):
                # Conversational match found! Produce natural contextual response
                lower = cleaned.lower()
                if any(k in lower or k in cleaned for k in ["thank", "thx", "appreciat", "شكر", "تسلم", "يعطيك"]):
                    return UserIntent.CONVERSATIONAL, CONVERSATIONAL_RESPONSES["thanks_ar" if is_ar else "thanks_en"]
                elif any(k in lower or k in cleaned for k in ["how are you", "what's up", "كيف حالك", "كيفك", "شخبارك"]):
                    return UserIntent.CONVERSATIONAL, CONVERSATIONAL_RESPONSES["how_are_you_ar" if is_ar else "how_are_you_en"]
                elif any(k in lower or k in cleaned for k in ["great", "awesome", "perfect", "nice", "ممتاز", "رائع", "تمام"]):
                    return UserIntent.CONVERSATIONAL, CONVERSATIONAL_RESPONSES["acknowledgement_ar" if is_ar else "acknowledgement_en"]
                elif any(k in lower or k in cleaned for k in ["bye", "goodbye", "مع السلامة", "وداعا"]):
                    return UserIntent.CONVERSATIONAL, CONVERSATIONAL_RESPONSES["goodbye_ar" if is_ar else "goodbye_en"]
                else:
                    return UserIntent.CONVERSATIONAL, CONVERSATIONAL_RESPONSES["greeting_ar" if is_ar else "greeting_en"]

        # Default is Knowledge query requiring RAG / context search
        return UserIntent.KNOWLEDGE, None

_INTENT_CLASSIFIER = IntentClassifier()

def get_intent_classifier() -> IntentClassifier:
    return _INTENT_CLASSIFIER
