"""M8 acceptance tests for epistemic outcomes and reasoning-provider fallback."""

from ai_core.response_engine import ResponseEngine


class OfflineModelGateway:
    def __init__(self):
        self.calls = 0

    def is_available(self):
        return False

    def chat(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("Unavailable provider must not be called")


class StubKnowledge:
    def __init__(self, result=None, error=None):
        self.result = result or {"success": False, "answer": "", "answer_status": "unknown"}
        self.error = error
        self.calls = 0

    def answer(self, question, preferred_language="hi"):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


def _format(engine, command, intent=None):
    return engine.format(
        command=command,
        result={"success": True, "stage": "conversation"},
        intent=intent or {"intent": "unknown", "target": command},
    )


def test_m8_conflicting_sources_are_explicitly_left_unresolved_in_hindi():
    gateway = OfflineModelGateway()
    knowledge = StubKnowledge({
        "success": False,
        "answer": "",
        "answer_status": "conflicting_sources",
        "sources": [{"title": "Source A"}, {"title": "Source B"}],
        "evidence": {"source_count": 2},
    })
    engine = ResponseEngine(model_gateway=gateway, knowledge_lookup=knowledge)

    answer = _format(engine, "भारत की राजधानी क्या है?")

    assert "असहमत" in answer
    assert "अनिर्णीत" in answer
    assert gateway.calls == 0


def test_m8_conflicting_sources_are_explicitly_left_unresolved_in_english():
    gateway = OfflineModelGateway()
    knowledge = StubKnowledge({
        "success": False,
        "answer": "",
        "answer_status": "conflicting_sources",
        "sources": [{"title": "Source A"}, {"title": "Source B"}],
    })
    engine = ResponseEngine(model_gateway=gateway, knowledge_lookup=knowledge)

    answer = _format(engine, "what is the disputed answer? answer in english")

    assert "sources disagree" in answer
    assert "unresolved" in answer
    assert gateway.calls == 0


def test_m8_weak_retrieved_evidence_is_not_presented_as_a_fact():
    gateway = OfflineModelGateway()
    knowledge = StubKnowledge({
        "success": False,
        "answer": "",
        "answer_status": "unknown",
        "reason": "weak_source_quality",
        "sources": [{"title": "Weak source", "url": "https://example.org/item"}],
        "evidence": {"source_count": 1, "source_quality": {"status": "weak"}},
    })
    engine = ResponseEngine(model_gateway=gateway, knowledge_lookup=knowledge)

    answer = _format(engine, "what is the answer? answer in english")

    assert "not strong enough" in answer
    assert "won't guess" in answer
    assert gateway.calls == 0


def test_m8_provider_outage_keeps_deterministic_conversation_fallback():
    gateway = OfflineModelGateway()
    knowledge = StubKnowledge()
    engine = ResponseEngine(model_gateway=gateway, knowledge_lookup=knowledge)

    answer = _format(
        engine,
        "how are you?",
        {"intent": "conversation", "conversation_type": "status"},
    )

    assert answer
    assert "बढ़िया" in answer
    assert gateway.calls == 0


def test_m8_knowledge_provider_exception_returns_safe_unknown_answer():
    gateway = OfflineModelGateway()
    knowledge = StubKnowledge(error=RuntimeError("simulated provider outage"))
    engine = ResponseEngine(model_gateway=gateway, knowledge_lookup=knowledge)

    answer = _format(engine, "what is photosynthesis? answer in english")

    assert "reliable answer" in answer
    assert "invent" not in answer.lower()
    assert gateway.calls == 0
