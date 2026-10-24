"""Fail-closed CI thresholds for the synthetic M10.2 benchmark report.

This checker evaluates reproducible harness/fixture conformance only. It does
not measure or certify live Vyom accuracy, safety, completion, or latency.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

from tools.vyom_benchmark_runner import load_json, write_json


RUNNER_METRICS = {
    "scenario_contract_conformance",
    "intent_interpretation_correctness",
    "unsafe_guess_rate",
    "action_verification_correctness",
    "task_completion_recovery_correctness",
    "epistemic_status_correctness",
}
COUNT_KEYS = {"total_scenarios", "selected_scenarios", "pass", "fail", "error", "unrun"}
POLICY_KEYS = {
    "schema_version", "policy_id", "policy_scope", "corpus_id",
    "required_scenario_ids", "expected_counts", "required_metrics",
    "product_accuracy_measured_must_be", "product_latency_measured_must_be",
    "product_latency_status_must_be", "note",
}


class ThresholdInputError(ValueError):
    """Invalid policy/report input; the CI gate must fail closed."""


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_policy(policy: Any) -> Dict[str, Any]:
    if not isinstance(policy, dict) or set(policy) != POLICY_KEYS:
        raise ThresholdInputError("policy_schema_invalid")
    if policy.get("schema_version") != 1 or isinstance(policy.get("schema_version"), bool):
        raise ThresholdInputError("policy_schema_unsupported")
    if policy.get("policy_scope") != "synthetic_harness_conformance_only":
        raise ThresholdInputError("policy_scope_invalid")
    for key in ("policy_id", "corpus_id", "note"):
        if not isinstance(policy.get(key), str) or not policy[key].strip():
            raise ThresholdInputError("policy_" + key + "_invalid")
    ids = policy.get("required_scenario_ids")
    if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or not x for x in ids):
        raise ThresholdInputError("policy_scenario_ids_invalid")
    if len(ids) != len(set(ids)):
        raise ThresholdInputError("policy_scenario_ids_duplicate")
    counts = policy.get("expected_counts")
    if not isinstance(counts, dict) or set(counts) != COUNT_KEYS:
        raise ThresholdInputError("policy_expected_counts_invalid")
    if any(not _is_int(counts[k]) or counts[k] < 0 for k in COUNT_KEYS):
        raise ThresholdInputError("policy_expected_counts_invalid")
    if counts["total_scenarios"] != len(ids) or counts["selected_scenarios"] != len(ids):
        raise ThresholdInputError("policy_scenario_count_mismatch")
    if counts["pass"] != len(ids) or counts["fail"] != 0 or counts["error"] != 0 or counts["unrun"] != 0:
        raise ThresholdInputError("policy_full_run_counts_invalid")
    metrics = policy.get("required_metrics")
    if not isinstance(metrics, dict) or set(metrics) != RUNNER_METRICS:
        raise ThresholdInputError("policy_metrics_invalid")
    for name, rule in metrics.items():
        if not isinstance(rule, dict):
            raise ThresholdInputError("policy_metric_rule_invalid:" + name)
        if set(rule) not in ({"expected_denominator", "min_rate"}, {"expected_denominator", "max_rate"}):
            raise ThresholdInputError("policy_metric_rule_invalid:" + name)
        denominator = rule["expected_denominator"]
        if not _is_int(denominator) or denominator <= 0:
            raise ThresholdInputError("policy_metric_denominator_invalid:" + name)
        threshold_key = "min_rate" if "min_rate" in rule else "max_rate"
        threshold = rule[threshold_key]
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
            raise ThresholdInputError("policy_metric_threshold_invalid:" + name)
    if policy["product_accuracy_measured_must_be"] is not False:
        raise ThresholdInputError("policy_accuracy_boundary_invalid")
    if policy["product_latency_measured_must_be"] is not False:
        raise ThresholdInputError("policy_latency_boundary_invalid")
    if policy["product_latency_status_must_be"] != "not_measured":
        raise ThresholdInputError("policy_latency_status_invalid")
    return policy


def evaluate_thresholds(report: Any, policy: Any) -> Dict[str, Any]:
    """Evaluate a report with deterministic checks; failures are a report, malformed input is an exception."""
    policy = validate_policy(policy)
    if not isinstance(report, dict) or report.get("report_schema_version") != 1:
        raise ThresholdInputError("report_schema_invalid")

    checks: List[Dict[str, Any]] = []

    def add(name: str, passed: bool, expected: Any, actual: Any, detail: str) -> None:
        checks.append({
            "check_id": name,
            "status": "pass" if passed else "fail",
            "expected": expected,
            "actual": actual,
            "detail": detail,
        })

    add("corpus_id", report.get("corpus_id") == policy["corpus_id"], policy["corpus_id"],
        report.get("corpus_id"), "Report must target the versioned M10.1 synthetic corpus.")
    add("execution_mode", report.get("execution_mode") == "offline_deterministic_synthetic_stub_adapter",
        "offline_deterministic_synthetic_stub_adapter", report.get("execution_mode"),
        "Thresholds only apply to the deterministic synthetic adapter.")
    add("measurement_scope", report.get("measurement_scope") == "harness_contract_conformance_only",
        "harness_contract_conformance_only", report.get("measurement_scope"),
        "Never broaden a fixture result into a product performance claim.")
    add("report_status", report.get("status") == "pass", "pass", report.get("status"),
        "A full regression run requires the report-level status to pass.")
    add("product_accuracy_boundary",
        report.get("product_accuracy_measured") is policy["product_accuracy_measured_must_be"],
        policy["product_accuracy_measured_must_be",] if False else False,
        report.get("product_accuracy_measured"),
        "Synthetic observations must not be labelled as measured product accuracy.")
    add("product_latency_boundary",
        report.get("product_latency_measured") is policy["product_latency_measured_must_be"],
        False, report.get("product_latency_measured"),
        "The stub adapter does not run or time the product.")
    
    counts = report.get("counts")
    counts_ok = isinstance(counts, dict) and set(counts) == COUNT_KEYS
    if counts_ok:
        counts_ok = all(_is_int(counts.get(key)) and counts.get(key) >= 0 for key in COUNT_KEYS)
    actual_counts = counts if isinstance(counts, dict) else None
    add("full_run_counts", counts_ok and counts == policy["expected_counts"],
        policy["expected_counts"], actual_counts,
        "All policy-required scenarios must be selected and pass; errors, failures and unrun rows block CI.")

    rows = report.get("scenarios")
    if not isinstance(rows, list):
        add("scenario_rows", False, len(policy["required_scenario_ids"]), None, "Scenario rows must be a list.")
        rows = []
    row_ids = [row.get("scenario_id") for row in rows if isinstance(row, dict)]
    ids_exact = row_ids == policy["required_scenario_ids"] and len(row_ids) == len(rows)
    add("scenario_ids_and_order", ids_exact, policy["required_scenario_ids"], row_ids,
        "The required full corpus must be present once each in stable order.")

    row_checks_pass = True
    for scenario_id in policy["required_scenario_ids"]:
        candidates = [row for row in rows if isinstance(row, dict) and row.get("scenario_id") == scenario_id]
        row = candidates[0] if len(candidates) == 1 else None
        row_ok = bool(
            row
            and row.get("run_status") == "pass"
            and row.get("outcome_match") is True
            and row.get("invariants_passed") is True
            and row.get("must_not_violations") == []
        )
        if not row_ok:
            row_checks_pass = False
            add("scenario:" + scenario_id, False, {
                "run_status": "pass", "outcome_match": True,
                "invariants_passed": True, "must_not_violations": [],
            }, row, "Every scenario must have a passing outcome and zero prohibited/invariant violations.")
    add("all_scenario_invariants", row_checks_pass, True, row_checks_pass,
        "No scenario may hide a prohibited outcome or invariant failure.")

    metrics = report.get("metrics")
    if not isinstance(metrics, dict):
        metrics = {}
    for name, rule in policy["required_metrics"].items():
        metric = metrics.get(name)
        if not isinstance(metric, dict):
            add("metric_present:" + name, False, "metric record", metric, "Required metric is missing.")
            continue
        denominator = rule["expected_denominator"]
        numerator = metric.get("numerator")
        actual_denominator = metric.get("denominator")
        sample_size = metric.get("sample_size")
        rate = metric.get("rate")
        metric_status_ok = metric.get("status") == "measured"
        numeric_ok = (
            _is_int(numerator) and 0 <= numerator <= denominator
            and _is_int(actual_denominator) and actual_denominator == denominator
            and _is_int(sample_size) and sample_size == denominator
            and not isinstance(rate, bool) and isinstance(rate, (int, float))
            and rate == round(numerator / denominator, 6)
        )
        add("metric_schema:" + name, metric_status_ok and numeric_ok, {
            "status": "measured", "expected_denominator": denominator,
            "sample_size": denominator, "rate": "round(numerator / denominator, 6)",
        }, {
            "status": metric.get("status"), "numerator": numerator,
            "denominator": actual_denominator, "sample_size": sample_size, "rate": rate,
        }, "Metric status, denominator, sample size and rate must be internally consistent.")
        if not numeric_ok:
            add("metric_threshold:" + name, False, rule, metric,
                "Threshold cannot pass without a valid, consistent metric record.")
            continue
        threshold_type = "min_rate" if "min_rate" in rule else "max_rate"
        threshold_value = rule[threshold_type]
        passed = rate >= threshold_value if threshold_type == "min_rate" else rate <= threshold_value
        add("metric_threshold:" + name, passed, {threshold_type: threshold_value, "denominator": denominator},
            {"rate": rate, "numerator": numerator, "denominator": actual_denominator},
            "Applied only to the synthetic fixture signal; it is not a product metric.")

    latency = metrics.get("product_latency_ms")
    latency_ok = (
        isinstance(latency, dict)
        and latency.get("status") == policy["product_latency_status_must_be"]
        and latency.get("denominator") == 0
        and latency.get("numerator") is None
        and latency.get("rate") is None
        and latency.get("metric_kind") == "unmeasured"
    )
    add("product_latency_unmeasured", latency_ok,
        {"status": "not_measured", "denominator": 0, "numerator": None, "rate": None, "metric_kind": "unmeasured"},
        latency, "Do not imply latency was measured by the synthetic stub.")

    passed_count = sum(1 for item in checks if item["status"] == "pass")
    failed_count = len(checks) - passed_count
    return {
        "report_schema_version": 1,
        "policy_id": policy["policy_id"],
        "policy_scope": policy["policy_scope"],
        "corpus_id": report.get("corpus_id"),
        "status": "pass" if failed_count == 0 else "fail",
        "check_counts": {"total": len(checks), "pass": passed_count, "fail": failed_count},
        "product_accuracy_measured": False,
        "product_latency_measured": False,
        "interpretation": "Synthetic harness regression gate only; this report is not evidence of live Vyom product accuracy, safety, task completion, or latency.",
        "checks": checks,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: List[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = load_json(args.report)
        policy = load_json(args.policy)
        gate = evaluate_thresholds(report, policy)
        write_json(args.output, gate)
        written = load_json(args.output)
        if written != gate:
            raise ThresholdInputError("written_gate_report_mismatch")
        print(json.dumps({
            "status": gate["status"],
            "check_counts": gate["check_counts"],
            "output": str(args.output),
            "product_accuracy_measured": False,
            "product_latency_measured": False,
        }, sort_keys=True))
        return 0 if gate["status"] == "pass" else 1
    except (ThresholdInputError, ValueError) as exc:
        print(f"M10_3_THRESHOLD_INPUT_ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"M10_3_THRESHOLD_RUNNER_ERROR: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
