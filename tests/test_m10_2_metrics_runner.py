"""M10.2 deterministic runner, denominator and reproducibility tests."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from tools.vyom_benchmark_runner import (
    BenchmarkInputError,
    DEFAULT_CORPUS,
    DEFAULT_OBSERVATIONS,
    build_report,
    build_summary,
    load_json,
    main,
)


def _inputs():
    return load_json(DEFAULT_CORPUS), load_json(DEFAULT_OBSERVATIONS)


def test_m10_2_full_stub_run_reports_every_scenario_and_explicit_denominators():
    corpus, observations = _inputs()
    report = build_report(corpus, observations)

    assert report["status"] == "pass"
    assert report["counts"] == {
        "total_scenarios": 15,
        "selected_scenarios": 15,
        "pass": 15,
        "fail": 0,
        "error": 0,
        "unrun": 0,
    }
    assert report["product_accuracy_measured"] is False
    assert report["product_latency_measured"] is False
    assert report["metrics"]["scenario_contract_conformance"]["numerator"] == 15
    assert report["metrics"]["scenario_contract_conformance"]["denominator"] == 15
    assert report["metrics"]["intent_interpretation_correctness"]["numerator"] == 6
    assert report["metrics"]["intent_interpretation_correctness"]["denominator"] == 6
    assert report["metrics"]["unsafe_guess_rate"]["numerator"] == 0
    assert report["metrics"]["unsafe_guess_rate"]["denominator"] == 15
    assert report["metrics"]["action_verification_correctness"]["denominator"] == 5
    assert report["metrics"]["task_completion_recovery_correctness"]["denominator"] == 4
    assert report["metrics"]["epistemic_status_correctness"]["denominator"] == 4
    assert report["metrics"]["product_latency_ms"]["status"] == "not_measured"
    assert report["metrics"]["product_latency_ms"]["denominator"] == 0
    assert "not a measurement" in build_summary(report)["interpretation"].lower()


def test_m10_2_report_is_byte_deterministic_for_fixed_inputs(tmp_path):
    corpus, observations = _inputs()
    report = build_report(corpus, observations)
    summary = build_summary(report)
    report_a, summary_a = tmp_path / "a.json", tmp_path / "summary-a.json"
    report_b, summary_b = tmp_path / "b.json", tmp_path / "summary-b.json"

    assert main(["--output", str(report_a), "--summary-output", str(summary_a)]) == 0
    assert main(["--output", str(report_b), "--summary-output", str(summary_b)]) == 0
    assert report_a.read_bytes() == report_b.read_bytes()
    assert summary_a.read_bytes() == summary_b.read_bytes()
    assert json.loads(report_a.read_text(encoding="utf-8")) == report
    assert json.loads(summary_a.read_text(encoding="utf-8")) == summary


def test_m10_2_unselected_scenarios_are_unrun_and_excluded_from_denominators():
    corpus, observations = _inputs()
    report = build_report(corpus, observations, ["m10-001-english-simple-open"])

    assert report["status"] == "partial"
    assert report["counts"]["pass"] == 1
    assert report["counts"]["unrun"] == 14
    assert report["metrics"]["scenario_contract_conformance"]["denominator"] == 1
    assert report["metrics"]["intent_interpretation_correctness"]["denominator"] == 1
    assert report["metrics"]["unsafe_guess_rate"]["denominator"] == 1
    assert report["metrics"]["epistemic_status_correctness"]["denominator"] == 0
    assert all(
        row["run_status"] == "unrun"
        for row in report["scenarios"]
        if row["scenario_id"] != "m10-001-english-simple-open"
    )


def test_m10_2_observed_outcome_mismatch_is_failed_not_passed():
    corpus, observations = _inputs()
    modified = deepcopy(observations)
    row = next(item for item in modified["observations"] if item["scenario_id"] == "m10-001-english-simple-open")
    row["observed_outcome"] = "clarification_required"

    report = build_report(corpus, modified)
    assert report["status"] == "fail"
    assert report["counts"]["fail"] == 1
    assert report["metrics"]["scenario_contract_conformance"]["numerator"] == 14
    assert report["metrics"]["scenario_contract_conformance"]["denominator"] == 15
    assert report["scenarios"][0]["rationale"] == "observed outcome differs from expected outcome"


def test_m10_2_missing_selected_observation_is_error_and_not_counted_as_pass():
    corpus, observations = _inputs()
    modified = deepcopy(observations)
    modified["observations"] = [
        item for item in modified["observations"]
        if item["scenario_id"] != "m10-015-provider-outage-factual-retrieval"
    ]

    report = build_report(corpus, modified)
    assert report["status"] == "fail"
    assert report["counts"]["error"] == 1
    assert report["counts"]["pass"] == 14
    assert report["metrics"]["scenario_contract_conformance"]["denominator"] == 14
    assert report["metrics"]["epistemic_status_correctness"]["denominator"] == 3


def test_m10_2_unknown_scenario_id_and_unknown_outcome_fail_closed():
    corpus, observations = _inputs()
    with pytest.raises(BenchmarkInputError, match="unknown_selected_scenario_id"):
        build_report(corpus, observations, ["m10-999-not-real"])

    modified = deepcopy(observations)
    modified["observations"][0]["observed_outcome"] = "invented_success"
    with pytest.raises(BenchmarkInputError, match="unknown_observed_outcome"):
        build_report(corpus, modified)


def test_m10_2_duplicate_or_invalid_signal_input_is_rejected():
    corpus, observations = _inputs()
    duplicated = deepcopy(observations)
    duplicated["observations"].append(deepcopy(duplicated["observations"][0]))
    with pytest.raises(BenchmarkInputError, match="duplicate_observation_scenario_id"):
        build_report(corpus, duplicated)

    bad_signals = deepcopy(observations)
    bad_signals["observations"][0]["signals"]["unsafe_guess"] = "false"
    with pytest.raises(BenchmarkInputError, match="signal_must_be_boolean"):
        build_report(corpus, bad_signals)


def test_m10_2_invariant_violation_causes_fail_even_if_outcome_matches():
    corpus, observations = _inputs()
    modified = deepcopy(observations)
    row = next(item for item in modified["observations"] if item["scenario_id"] == "m10-009-conflicting-web-sources")
    row["invariants_passed"] = False
    row["must_not_violations"] = ["selected a source by heuristic score"]

    report = build_report(corpus, modified)
    result = next(item for item in report["scenarios"] if item["scenario_id"] == row["scenario_id"])
    assert result["run_status"] == "fail"
    assert "stub invariant signal failed" in result["rationale"]
    assert result["must_not_violations"]


def test_m10_2_runner_rejects_duplicate_selected_scenario_ids():
    corpus, observations = _inputs()
    with pytest.raises(BenchmarkInputError, match="duplicate_selected_scenario_id"):
        build_report(corpus, observations, ["m10-001-english-simple-open", "m10-001-english-simple-open"])
