"""Deterministic tests for the M10.3 synthetic regression threshold gate."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from tools.vyom_benchmark_runner import (
    DEFAULT_CORPUS,
    DEFAULT_OBSERVATIONS,
    build_report,
    load_json,
)
from tools.vyom_benchmark_thresholds import (
    ThresholdInputError,
    evaluate_thresholds,
    main,
    validate_policy,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "tests" / "fixtures" / "m10_3_regression_thresholds.json"


def _inputs():
    corpus = load_json(DEFAULT_CORPUS)
    observations = load_json(DEFAULT_OBSERVATIONS)
    policy = load_json(DEFAULT_POLICY)
    return build_report(corpus, observations), policy


def test_m10_3_full_fixture_baseline_passes_and_labels_scope_as_synthetic():
    report, policy = _inputs()
    gate = evaluate_thresholds(report, policy)

    assert gate["status"] == "pass"
    assert gate["check_counts"]["fail"] == 0
    assert gate["product_accuracy_measured"] is False
    assert gate["product_latency_measured"] is False
    assert "not evidence" in gate["interpretation"].lower()
    assert any(item["check_id"] == "product_latency_unmeasured" and item["status"] == "pass"
               for item in gate["checks"])


def test_m10_3_is_deterministic_for_fixed_report_and_policy(tmp_path):
    report, policy = _inputs()
    report_path = tmp_path / "report.json"
    policy_path = tmp_path / "policy.json"
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    assert main(["--report", str(report_path), "--policy", str(policy_path), "--output", str(first)]) == 0
    assert main(["--report", str(report_path), "--policy", str(policy_path), "--output", str(second)]) == 0
    assert first.read_bytes() == second.read_bytes()


def test_m10_3_contract_or_invariant_regression_blocks_gate():
    report, policy = _inputs()
    changed = deepcopy(report)
    changed["scenarios"][8]["invariants_passed"] = False
    changed["scenarios"][8]["must_not_violations"] = ["heuristic selected a source"]
    gate = evaluate_thresholds(changed, policy)

    assert gate["status"] == "fail"
    assert any(x["check_id"] == "all_scenario_invariants" and x["status"] == "fail" for x in gate["checks"])


def test_m10_3_missing_unrun_or_error_scenarios_block_full_run_gate():
    report, policy = _inputs()
    for counts, status in [
        ({"total_scenarios": 15, "selected_scenarios": 14, "pass": 14, "fail": 0, "error": 0, "unrun": 1}, "partial"),
        ({"total_scenarios": 15, "selected_scenarios": 15, "pass": 14, "fail": 0, "error": 1, "unrun": 0}, "fail"),
    ]:
        changed = deepcopy(report)
        changed["counts"] = counts
        changed["status"] = status
        gate = evaluate_thresholds(changed, policy)
        assert gate["status"] == "fail"


def test_m10_3_missing_metric_wrong_denominator_or_inconsistent_rate_fails():
    report, policy = _inputs()
    missing = deepcopy(report)
    del missing["metrics"]["epistemic_status_correctness"]
    assert evaluate_thresholds(missing, policy)["status"] == "fail"

    wrong_denominator = deepcopy(report)
    wrong_denominator["metrics"]["intent_interpretation_correctness"]["denominator"] = 5
    assert evaluate_thresholds(wrong_denominator, policy)["status"] == "fail"

    inconsistent_rate = deepcopy(report)
    inconsistent_rate["metrics"]["unsafe_guess_rate"]["rate"] = 0.2
    assert evaluate_thresholds(inconsistent_rate, policy)["status"] == "fail"


def test_m10_3_unsafe_guess_signal_breach_blocks_gate():
    report, policy = _inputs()
    changed = deepcopy(report)
    changed["metrics"]["unsafe_guess_rate"]["numerator"] = 1
    changed["metrics"]["unsafe_guess_rate"]["rate"] = round(1 / 15, 6)
    gate = evaluate_thresholds(changed, policy)
    assert gate["status"] == "fail"
    assert any(x["check_id"] == "metric_threshold:unsafe_guess_rate" and x["status"] == "fail"
               for x in gate["checks"])


def test_m10_3_rejects_product_accuracy_or_latency_claims_from_stub():
    report, policy = _inputs()
    changed = deepcopy(report)
    changed["product_accuracy_measured"] = True
    assert evaluate_thresholds(changed, policy)["status"] == "fail"

    changed = deepcopy(report)
    changed["product_latency_measured"] = True
    changed["metrics"]["product_latency_ms"]["status"] = "measured"
    changed["metrics"]["product_latency_ms"]["denominator"] = 15
    assert evaluate_thresholds(changed, policy)["status"] == "fail"


def test_m10_3_invalid_policy_and_unknown_metric_fail_closed():
    _, policy = _inputs()
    invalid = deepcopy(policy)
    invalid["required_metrics"]["new_metric"] = {"expected_denominator": 1, "min_rate": 1.0}
    with pytest.raises(ThresholdInputError, match="policy_metrics_invalid"):
        validate_policy(invalid)

    invalid = deepcopy(policy)
    invalid["required_scenario_ids"].append(invalid["required_scenario_ids"][0])
    with pytest.raises(ThresholdInputError, match="policy_scenario_ids_duplicate"):
        validate_policy(invalid)


def test_m10_3_scenario_list_must_match_exact_required_order():
    report, policy = _inputs()
    report["scenarios"] = list(reversed(report["scenarios"]))
    gate = evaluate_thresholds(report, policy)
    assert gate["status"] == "fail"
    assert any(x["check_id"] == "scenario_ids_and_order" and x["status"] == "fail" for x in gate["checks"])


def test_m10_3_cli_returns_nonzero_and_writes_gate_report_on_threshold_failure(tmp_path):
    report, policy = _inputs()
    report["status"] = "fail"
    report_path = tmp_path / "report.json"
    policy_path = tmp_path / "policy.json"
    output_path = tmp_path / "gate.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    code = main(["--report", str(report_path), "--policy", str(policy_path), "--output", str(output_path)])
    assert code == 1
    gate = json.loads(output_path.read_text(encoding="utf-8"))
    assert gate["status"] == "fail"
    assert gate["check_counts"]["fail"] > 0
