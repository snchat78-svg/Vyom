"""M10.1 contract tests for the synthetic representative benchmark corpus."""
import json
from pathlib import Path
import re

CORPUS_PATH = Path(__file__).parent / "fixtures" / "m10_1_vyom_benchmark_corpus.json"
REQUIRED_CATEGORIES = {
    "english", "hindi", "roman_hindi", "hinglish", "noisy_stt", "ambiguity",
    "compound_task", "web_grounding", "unknown_factual", "conflicting_sources",
    "provider_outage", "recovery", "verification", "memory_safety",
}
ALLOWED_LANGUAGES = {"english", "hindi", "roman_hindi", "hinglish"}
ALLOWED_OUTCOMES = {
    "single_supported_action", "verified_unique_target_or_clarification",
    "ordered_multi_step_goal", "clarification_required",
    "ordered_mission_with_dependencies", "cited_answer_or_honest_unknown",
    "unknown_without_fabrication", "conflict_unresolved", "deterministic_fallback",
    "blocked_pending_user_resolution", "not_success_without_verification",
    "memory_hints_disabled", "unsafe_memory_value_ignored", "honest_unknown",
}
FORBIDDEN_SECRET_PATTERNS = (
    re.compile(r"(?i)api[_ -]?key\s*[:=]"),
    re.compile(r"(?i)password\s*[:=]"),
    re.compile(r"(?i)bearer\s+[a-z0-9._-]{12,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def _load_corpus():
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def test_m10_1_corpus_is_synthetic_and_does_not_claim_measured_results():
    corpus = _load_corpus()
    assert corpus["schema_version"] == 1
    assert corpus["execution_status"] == "contract_only_not_benchmarked"
    assert corpus["privacy"] == {
        "contains_real_user_content": False,
        "contains_credentials": False,
        "contains_raw_transcripts": False,
        "fixture_policy": "Synthetic examples only; do not add real private conversations or credentials.",
    }
    encoded = json.dumps(corpus, ensure_ascii=False)
    for pattern in FORBIDDEN_SECRET_PATTERNS:
        assert not pattern.search(encoded)
    for scenario in corpus["scenarios"]:
        assert "observed_result" not in scenario
        assert "measured_metrics" not in scenario


def test_m10_1_corpus_covers_every_required_language_and_safety_category():
    corpus = _load_corpus()
    assert set(corpus["required_categories"]) == REQUIRED_CATEGORIES
    observed = {category for scenario in corpus["scenarios"] for category in scenario["categories"]}
    assert REQUIRED_CATEGORIES.issubset(observed)
    assert {scenario["language"] for scenario in corpus["scenarios"]} == ALLOWED_LANGUAGES


def test_m10_1_scenario_contracts_are_complete_unique_and_bounded():
    corpus = _load_corpus()
    scenarios = corpus["scenarios"]
    assert 10 <= len(scenarios) <= 64
    ids = [scenario["id"] for scenario in scenarios]
    assert len(ids) == len(set(ids))
    for scenario in scenarios:
        assert scenario["id"].startswith("m10-")
        assert scenario["categories"]
        assert set(scenario["categories"]).issubset(REQUIRED_CATEGORIES)
        assert scenario["language"] in ALLOWED_LANGUAGES
        assert isinstance(scenario["input"], str) and 0 < len(scenario["input"]) <= 2000
        assert isinstance(scenario["preconditions"], dict)
        contract = scenario["expected_contract"]
        assert contract["outcome"] in ALLOWED_OUTCOMES
        assert contract["must_hold"] and contract["must_not"]
        assert all(isinstance(item, str) and item.strip() for item in contract["must_hold"])
        assert all(isinstance(item, str) and item.strip() for item in contract["must_not"])


def test_m10_1_critical_safety_contracts_remain_explicit():
    by_id = {item["id"]: item for item in _load_corpus()["scenarios"]}
    assert by_id["m10-005-ambiguous-ui-target"]["expected_contract"]["outcome"] == "clarification_required"
    assert by_id["m10-009-conflicting-web-sources"]["expected_contract"]["outcome"] == "conflict_unresolved"
    assert by_id["m10-011-uncertain-action-recovery"]["expected_contract"]["outcome"] == "blocked_pending_user_resolution"
    assert by_id["m10-012-unverified-save"]["expected_contract"]["outcome"] == "not_success_without_verification"
    memory_contract = by_id["m10-014-memory-injection-payload"]["expected_contract"]
    assert memory_contract["outcome"] == "unsafe_memory_value_ignored"
    assert any("bypass confirmation" in item.lower() for item in memory_contract["must_not"])
