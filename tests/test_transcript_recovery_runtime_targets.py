"""M1 acceptance tests for runtime-backed noisy target recovery."""

from ai_core.transcript_recovery import TranscriptRecovery
from ai_core.semantic_brain import LocalSemanticBrain


_OPERATION_PHRASES = {
    "open": ("open", "launch"),
    "close": ("close", "exit"),
}


def _tied_target_similarity(cls, left, right):
    left_key = cls._normalize(left).casefold()
    right_key = cls._normalize(right).casefold()
    scores = {
        ("calclulator", "calculator"): 0.91,
        ("calclulator", "calculater"): 0.89,
    }
    return scores.get((left_key, right_key), 0.0)


def test_clear_runtime_candidate_recovers_a_target_typo_and_keeps_raw_transcript():
    transcript = "open calcultor"
    recovery = TranscriptRecovery().recover(
        transcript,
        _OPERATION_PHRASES,
        context={"runtime_candidates": ["Calculator"]},
    )

    assert recovery["raw_transcript"] == transcript
    assert recovery["text"] == "open Calculator"
    assert recovery["changed"] is True
    assert any(
        correction["kind"] == "runtime_target"
        and correction["observed"] == "calcultor"
        and correction["recovered"] == "Calculator"
        and correction["margin"] >= 0.10
        for correction in recovery["corrections"]
    )


def test_near_tied_runtime_candidates_leave_target_unchanged_and_report_ambiguity(monkeypatch):
    monkeypatch.setattr(
        TranscriptRecovery,
        "_similarity",
        classmethod(_tied_target_similarity),
    )
    transcript = "open calclulator"
    recovery = TranscriptRecovery().recover(
        transcript,
        _OPERATION_PHRASES,
        context={"runtime_candidates": ["Calculator", "Calculater"]},
    )

    assert recovery["text"] == transcript
    assert recovery["changed"] is False
    assert recovery["corrections"] == []
    assert len(recovery["ambiguities"]) == 1
    ambiguity = recovery["ambiguities"][0]
    assert ambiguity["operation"] == "open"
    assert ambiguity["observed"] == "calclulator"
    assert [candidate["value"] for candidate in ambiguity["candidates"]] == [
        "Calculator", "Calculater",
    ]


def test_semantic_brain_blocks_dispatch_when_runtime_target_is_tied(monkeypatch):
    monkeypatch.setattr(
        TranscriptRecovery,
        "_similarity",
        classmethod(_tied_target_similarity),
    )
    brain = LocalSemanticBrain()

    def existing_pipeline(_goal, context=None):
        return {
            "success": True,
            "route": "capability",
            "message": "Prepared an application-open action.",
            "confidence": 0.91,
            "plan": [{
                "type": "action",
                "action": "open_application",
                "target": "calclulator",
                "args": {},
                "status": "pending",
            }],
            "source": "local_semantic_brain",
        }

    monkeypatch.setattr(brain, "_reason_existing_pipeline", existing_pipeline)
    result = brain.reason(
        "open calclulator",
        context={"runtime_candidates": ["Calculator", "Calculater"]},
    )

    assert result["route"] == "clarification"
    assert result["plan"] == []
    assert result["needs_confirmation"] is True
    assert result["terminal"] is True
    assert result["semantic_interpretation"][0]["reason"] == "ambiguous_runtime_target"
    assert "Calculator" in result["message"]
    assert "Calculater" in result["message"]
