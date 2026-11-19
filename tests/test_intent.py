import pytest
from backend.app.services.intent import IntentClassifier, UserIntent

@pytest.fixture
def classifier():
    return IntentClassifier()

def test_english_greetings(classifier):
    queries = ["Hello", "Hi there!", "Good morning", "Hey! How are you?"]
    for q in queries:
        intent, response = classifier.classify(q)
        assert intent == UserIntent.CONVERSATIONAL, f"Failed for {q}"
        assert response is not None

def test_arabic_greetings(classifier):
    queries = ["مرحبا", "أهلاً وسهلاً", "السلام عليكم", "صباح الخير"]
    for q in queries:
        intent, response = classifier.classify(q)
        assert intent == UserIntent.CONVERSATIONAL, f"Failed for {q}"
        assert response is not None
        assert classifier.is_arabic(response)

def test_gratitude(classifier):
    en_intent, _ = classifier.classify("Thank you very much")
    ar_intent, _ = classifier.classify("شكراً جزيلاً لك")
    assert en_intent == UserIntent.CONVERSATIONAL
    assert ar_intent == UserIntent.CONVERSATIONAL

def test_knowledge_questions(classifier):
    queries_en = [
        "What is the company vacation policy?",
        "Explain section 4 of the financial report",
        "Summarize the attached contract"
    ]
    for q in queries_en:
        intent, response = classifier.classify(q)
        assert intent == UserIntent.KNOWLEDGE, f"Incorrectly marked {q} as conversational"
        assert response is None

    queries_ar = [
        "ما هي سياسة الإجازات في الشركة؟",
        "اشرح الفقرة الرابعة من التقرير المالي",
        "لخص العقد المرفق"
    ]
    for q in queries_ar:
        intent, response = classifier.classify(q)
        assert intent == UserIntent.KNOWLEDGE, f"Incorrectly marked {q} as conversational"
        assert response is None

def test_noise_filtering(classifier):
    noise_samples = ["", " ", "...", "?!", "---"]
    for n in noise_samples:
        intent, _ = classifier.classify(n)
        assert intent == UserIntent.NOISE
