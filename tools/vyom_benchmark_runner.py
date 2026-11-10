"""Deterministic offline runner for Vyom's M10 benchmark contract fixtures.

This runner evaluates only synthetic adapter observations. Its metrics are a
reproducible harness baseline, NOT measured product accuracy, safety, or latency.
No web, model, microphone, or desktop integration is invoked.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List, Optional


RUNNER_VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "tests" / "fixtures" / "m10_1_vyom_benchmark_corpus.json"
DEFAULT_OBSERVATIONS = ROOT / "tests" / "fixtures" / "m10_2_stub_observations.json"
ALLOWED_OUTCOMES = {
    "single_supported_action",
    "verified_unique_target_or_clarification",
    "ordered_multi_step_goal",
    "clarification_required",
    "ordered_mission_with_dependencies",
    "cited_answer_or_honest_unknown",
    "unknown_without_fabrication",
    "conflict_unresolved",
    "deterministic_fallback",
    "blocked_pending_user_resolution",
    "not_success_without_verification",
    "memory_hints_disabled",
    "unsafe_memory_value_ignored",
    "honest_unknown",
}
SIGNAL_KEYS = {
    "intent_interpretation_applicable",
    "intent_interpretation_correct",
    "unsafe_guess_observable",
    "unsafe_guess",
    "action_verification_applicable",
    "action_verification_correct",
    "completion_recovery_applicable",
    "completion_recovery_correct",
    "epistemic_status_applicable",
    "epistemic_status_correct",
}


class BenchmarkInputError(ValueError):
    """Raised when a corpus or adapter input violates the versioned contract."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise BenchmarkInputError(f"json_read_failed:{Path(path).name}") from exc


def validate_corpus(corpus: Any) -> List[Dict[str, Any]]:
    if not isinstance(corpus, dict):
        raise BenchmarkInputError("corpus_must_be_object")
    if corpus.get("schema_version") != 1:
        raise BenchmarkInputError("unsupported_corpus_schema")
    if corpus.get("execution_status") != "contract_only_not_benchmarked":
        raise BenchmarkInputError("unexpected_corpus_execution_status")
    scenarios = corpus.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise BenchmarkInputError("corpus_scenarios_missing")
    seen = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise BenchmarkInputError("scenario_must_be_object")
        scenario_id = scenario.get("id")
        if not isinstance(scenario_id, str) or not scenario_id.startswith("m10-"):
            raise BenchmarkInputError("invalid_scenario_id")
        if scenario_id in seen:
            raise BenchmarkInputError("duplicate_scenario_id")
        seen.add(scenario_id)
        contract = scenario.get("expected_contract")
        if not isinstance(contract, dict):
            raise BenchmarkInputError(f"{scenario_id}:expected_contract_missing")
        if contract.get("outcome") not in ALLOWED_OUTCOMES:
            raise BenchmarkInputError(f"{scenario_id}:unknown_expected_outcome")
        if not isinstance(contract.get("must_hold"), list) or not contract["must_hold"]:
            raise BenchmarkInputError(f"{scenario_id}:must_hold_missing")
        if not isinstance(contract.get("must_not"), list) or not contract["must_not"]:
            raise BenchmarkInputError(f"{scenario_id}:must_not_missing")
    return scenarios


def validate_observations(observations: Any, scenario_ids: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(observations, dict) or observations.get("schema_version") != 1:
        raise BenchmarkInputError("unsupported_observations_schema")
    if observations.get("adapter_mode") != "deterministic_synthetic_stub":
        raise BenchmarkInputError("unsupported_adapter_mode")
    rows = observations.get("observations")
    if not isinstance(rows, list):
        raise BenchmarkInputError("observations_must_be_list")

    known_ids = set(scenario_ids)
    result: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise BenchmarkInputError("observation_must_be_object")
        scenario_id = row.get("scenario_id")
        if not isinstance(scenario_id, str) or scenario_id not in known_ids:
            raise BenchmarkInputError("unknown_observation_scenario_id")
        if scenario_id in result:
            raise BenchmarkInputError("duplicate_observation_scenario_id")
        outcome = row.get("observed_outcome")
        if outcome not in ALLOWED_OUTCOMES:
            raise BenchmarkInputError(f"{scenario_id}:unknown_observed_outcome")
        if row.get("invariants_passed") is not True:
            if row.get("invariants_passed") is not False:
                raise BenchmarkInputError(f"{scenario_id}:invalid_invariants_flag")
        violations = row.get("must_not_violations")
        if not isinstance(violations, list) or not all(isinstance(item, str) for item in violations):
            raise BenchmarkInputError(f"{scenario_id}:invalid_violation_list")
        signals = row.get("signals")
        if not isinstance(signals, dict) or set(signals) != SIGNAL_KEYS:
            raise BenchmarkInputError(f"{scenario_id}:invalid_signal_schema")
        if any(type(signals[key]) is not bool for key in SIGNAL_KEYS):
            raise BenchmarkInputError(f"{scenario_id}:signal_must_be_boolean")
        result[scenario_id] = row
    return result


def _metric_record(
    *,
    numerator: int,
    denominator: int,
    scope: str,
    formula: str,
    metric_kind: str,
) -> Dict[str, Any]:
    return {
        "status": "measured" if denominator > 0 else "not_measured",
        "numerator": numerator if denominator > 0 else None,
        "denominator": denominator,
        "sample_size": denominator,
        "rate": round(numerator / denominator, 6) if denominator > 0 else None,
        "scope": scope,
        "metric_kind": metric_kind,
        "formula": formula,
    }


def _aggregate_metrics(scenario_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Metrics are aggregated only from selected scenarios with valid observations.
    usable = [row for row in scenario_results if row["run_status"] in {"pass", "fail"}]
    matched = sum(1 for row in usable if row["outcome_match"] and row["invariants_passed"] and not row["must_not_violations"])

    metrics: Dict[str, Any] = {
        "scenario_contract_conformance": _metric_record(
            numerator=matched,
            denominator=len(usable),
            scope="synthetic_adapter_contract_labels",
            formula="valid observed scenarios satisfying expected outcome and stub invariant signal / valid observed scenarios",
            metric_kind="harness_conformance_not_product_accuracy",
        )
    }

    specs = [
        ("intent_interpretation_correctness", "intent_interpretation_applicable", "intent_interpretation_correct",
         "correct intent fixture signals / executed intent-applicable fixture scenarios"),
        ("action_verification_correctness", "action_verification_applicable", "action_verification_correct",
         "correct verification fixture signals / executed verification-applicable fixture scenarios"),
        ("task_completion_recovery_correctness", "completion_recovery_applicable", "completion_recovery_correct",
         "correct completion/recovery fixture signals / executed applicable fixture scenarios"),
        ("epistemic_status_correctness", "epistemic_status_applicable", "epistemic_status_correct",
         "correct epistemic-status fixture signals / executed epistemic-applicable fixture scenarios"),
    ]
    for name, applicable_key, correct_key, formula in specs:
        eligible = [
            row for row in usable
            if row["observed_signals"][applicable_key] is True
        ]
        numerator = sum(1 for row in eligible if row["observed_signals"][correct_key] is True)
        metrics[name] = _metric_record(
            numerator=numerator,
            denominator=len(eligible),
            scope="synthetic_adapter_signals_not_product_behavior",
            formula=formula,
            metric_kind="synthetic_stub_baseline_not_product_accuracy",
        )

    unsafe_eligible = [
        row for row in usable
        if row["observed_signals"]["unsafe_guess_observable"] is True
    ]
    unsafe_count = sum(1 for row in unsafe_eligible if row["observed_signals"]["unsafe_guess"] is True)
    metrics["unsafe_guess_rate"] = _metric_record(
        numerator=unsafe_count,
        denominator=len(unsafe_eligible),
        scope="synthetic_adapter_signals_not_product_behavior",
        formula="stub-observed unsafe-guess flags / executed scenarios where the fixture marks unsafe guessing observable",
        metric_kind="synthetic_stub_baseline_not_product_safety_rate",
    )

    metrics["product_latency_ms"] = {
        "status": "not_measured",
        "numerator": None,
        "denominator": 0,
        "sample_size": 0,
        "rate": None,
        "scope": "actual Vyom runtime",
        "metric_kind": "unmeasured",
        "formula": None,
        "reason": "The deterministic stub adapter does not invoke or time the Vyom product; collect latency only in a defined runtime integration harness (M10.4).",
    }
    return metrics


def build_report(
    corpus: Any,
    observations_document: Any,
    scenario_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    scenarios = validate_corpus(corpus)
    corpus_ids = [item["id"] for item in scenarios]
    observations = validate_observations(observations_document, corpus_ids)

    if scenario_ids is None:
        selected = set(corpus_ids)
    else:
        if len(scenario_ids) != len(set(scenario_ids)):
            raise BenchmarkInputError("duplicate_selected_scenario_id")
        unknown = set(scenario_ids) - set(corpus_ids)
        if unknown:
            raise BenchmarkInputError("unknown_selected_scenario_id")
        selected = set(scenario_ids)

    rows: List[Dict[str, Any]] = []
    for scenario in scenarios:
        scenario_id = scenario["id"]
        contract = scenario["expected_contract"]
        base = {
            "scenario_id": scenario_id,
            "language": scenario["language"],
            "categories": list(scenario["categories"]),
            "expected_outcome": contract["outcome"],
            "declared_must_hold": list(contract["must_hold"]),
            "declared_must_not": list(contract["must_not"]),
        }

        if scenario_id not in selected:
            rows.append({
                **base,
                "run_status": "unrun",
                "observed_outcome": None,
                "outcome_match": None,
                "invariants_passed": None,
                "must_not_violations": [],
                "observed_signals": None,
                "rationale": "Scenario was not selected for this run; it is excluded from all metric denominators.",
                "observation_source": None,
            })
            continue

        observation = observations.get(scenario_id)
        if observation is None:
            rows.append({
                **base,
                "run_status": "error",
                "observed_outcome": None,
                "outcome_match": None,
                "invariants_passed": None,
                "must_not_violations": [],
                "observed_signals": None,
                "rationale": "No deterministic adapter observation exists for this selected scenario; it is not counted as a pass.",
                "observation_source": "missing_stub_observation",
            })
            continue

        observed = observation["observed_outcome"]
        outcome_match = observed == contract["outcome"]
        violations = list(observation["must_not_violations"])
        invariants_passed = observation["invariants_passed"]
        status = "pass" if outcome_match and invariants_passed and not violations else "fail"
        if status == "pass":
            rationale = "The deterministic synthetic adapter emitted the expected label and no stub invariant violation. This validates harness/oracle wiring only, not application behavior."
        else:
            parts = []
            if not outcome_match:
                parts.append("observed outcome differs from expected outcome")
            if not invariants_passed:
                parts.append("stub invariant signal failed")
            if violations:
                parts.append("stub reports prohibited outcome(s)")
            rationale = "; ".join(parts)

        rows.append({
            **base,
            "run_status": status,
            "observed_outcome": observed,
            "outcome_match": outcome_match,
            "invariants_passed": invariants_passed,
            "must_not_violations": violations,
            "observed_signals": dict(observation["signals"]),
            "rationale": rationale,
            "observation_source": observations_document["adapter_mode"],
        })

    counts = {
        "total_scenarios": len(rows),
        "selected_scenarios": len(selected),
        "pass": sum(1 for row in rows if row["run_status"] == "pass"),
        "fail": sum(1 for row in rows if row["run_status"] == "fail"),
        "error": sum(1 for row in rows if row["run_status"] == "error"),
        "unrun": sum(1 for row in rows if row["run_status"] == "unrun"),
    }
    if counts["fail"] or counts["error"]:
        status = "fail"
    elif counts["unrun"]:
        status = "partial"
    else:
        status = "pass"

    report = {
        "report_schema_version": 1,
        "runner_version": RUNNER_VERSION,
        "corpus_id": corpus["corpus_id"],
        "corpus_schema_version": corpus["schema_version"],
        "corpus_source_status": corpus["execution_status"],
        "execution_mode": "offline_deterministic_synthetic_stub_adapter",
        "measurement_scope": "harness_contract_conformance_only",
        "product_accuracy_measured": False,
        "product_latency_measured": False,
        "status": status,
        "counts": counts,
        "selected_scenario_ids": [scenario_id for scenario_id in corpus_ids if scenario_id in selected],
        "scenarios": rows,
        "metrics": _aggregate_metrics(rows),
        "exclusions": [
            {
                "metric": "product_latency_ms",
                "reason": "No product runtime or wall-clock performance is measured by the synthetic adapter; this metric requires a separately defined runtime harness.",
            },
            {
                "metric": "all product_accuracy_or_safety_rates",
                "reason": "The adapter observations are fixed synthetic fixtures, not executions of the Vyom application; do not publish these rates as product accuracy or safety.",
            },
        ],
    }
    return report


def build_summary(report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "summary_schema_version": 1,
        "runner_version": report["runner_version"],
        "corpus_id": report["corpus_id"],
        "corpus_schema_version": report["corpus_schema_version"],
        "execution_mode": report["execution_mode"],
        "measurement_scope": report["measurement_scope"],
        "product_accuracy_measured": report["product_accuracy_measured"],
        "product_latency_measured": report["product_latency_measured"],
        "status": report["status"],
        "counts": dict(report["counts"]),
        "metrics": deepcopy(report["metrics"]),
        "interpretation": "Synthetic adapter baseline only; this is not a measurement of live Vyom accuracy, safety, task completion, or latency.",
    }


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    path.write_text(encoded, encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--observations", type=Path, default=DEFAULT_OBSERVATIONS)
    parser.add_argument("--output", type=Path, required=True, help="Path for the machine-readable scenario report.")
    parser.add_argument("--summary-output", type=Path, required=True, help="Path for the reproducible metrics summary.")
    parser.add_argument("--scenario-id", action="append", dest="scenario_ids", help="Run only this scenario ID; repeat to select more. Others are reported as unrun.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        corpus = load_json(args.corpus)
        observations = load_json(args.observations)
        report = build_report(corpus, observations, args.scenario_ids)
        summary = build_summary(report)
        write_json(args.output, report)
        write_json(args.summary_output, summary)

        # Reload and validate the written artifacts so a successful exit implies
        # the two machine-readable outputs can be parsed and are self-consistent.
        written_report = load_json(args.output)
        written_summary = load_json(args.summary_output)
        if written_report != report or written_summary != summary:
            raise BenchmarkInputError("written_report_validation_failed")
        if written_summary["counts"] != written_report["counts"]:
            raise BenchmarkInputError("report_summary_count_mismatch")
        print(json.dumps({
            "status": report["status"],
            "counts": report["counts"],
            "output": str(args.output),
            "summary_output": str(args.summary_output),
            "product_accuracy_measured": False,
            "product_latency_measured": False,
        }, sort_keys=True))
        return 1 if report["counts"]["fail"] or report["counts"]["error"] else 0
    except BenchmarkInputError as exc:
        print(f"BENCHMARK_INPUT_ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"BENCHMARK_RUNNER_ERROR: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
