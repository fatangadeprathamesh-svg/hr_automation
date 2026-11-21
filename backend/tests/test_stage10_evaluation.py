import json
from pathlib import Path
import pytest
from evaluation.evaluate_rules import run_benchmark, RULE_REGISTRY

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_PATH = REPO_ROOT / "evaluation" / "ground_truth_dataset.json"
REPORT_PATH = REPO_ROOT / "evaluation" / "benchmark_report.json"


def test_ground_truth_dataset_structure():
    """Verify ground truth dataset exists, is valid JSON, and covers all 9 rules."""
    assert DATASET_PATH.exists(), f"Missing ground truth dataset at {DATASET_PATH}"
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "version" in data
    assert "cases" in data
    cases = data["cases"]
    assert len(cases) >= 25, f"Expected at least 25 cases, got {len(cases)}"

    # Ensure all 9 deterministic rules are covered
    covered_rules = {c["rule_id"] for c in cases}
    expected_rules = set(RULE_REGISTRY.keys())
    assert covered_rules == expected_rules, f"Missing rules: {expected_rules - covered_rules}"


def test_rule_engine_benchmark_accuracy():
    """Verify 100% precision, 100% recall, 0 FP, 0 FN, and 100% data health accuracy."""
    report = run_benchmark(DATASET_PATH)
    gm = report["global_metrics"]

    # Zero False Positives -> 100% Precision
    assert gm["fp"] == 0, f"Expected 0 False Positives, got {gm['fp']}"
    assert gm["precision"] == 1.0, f"Expected 1.0 Precision, got {gm['precision']}"

    # Zero False Negatives -> 100% Recall
    assert gm["fn"] == 0, f"Expected 0 False Negatives, got {gm['fn']}"
    assert gm["recall"] == 1.0, f"Expected 1.0 Recall, got {gm['recall']}"

    # F1-Score & Accuracy
    assert gm["f1_score"] == 1.0
    assert gm["accuracy"] == 1.0

    # Non-negotiable Rule 3: Zero false accusations on missing/corrupt data
    assert gm["data_health_accuracy"] == 1.0, f"Expected 1.0 Data Health handling, got {gm['data_health_accuracy']}"


def test_per_rule_benchmark_performance():
    """Verify that every single rule independently achieves 100% precision and 100% recall."""
    report = run_benchmark(DATASET_PATH)
    per_rule = report["per_rule_metrics"]

    assert len(per_rule) == 9
    for rule_id, metrics in per_rule.items():
        assert metrics["fp"] == 0, f"Rule {rule_id} generated {metrics['fp']} False Positives"
        assert metrics["fn"] == 0, f"Rule {rule_id} generated {metrics['fn']} False Negatives"
        assert metrics["precision"] == 1.0, f"Rule {rule_id} precision is {metrics['precision']}"
        assert metrics["recall"] == 1.0, f"Rule {rule_id} recall is {metrics['recall']}"


def test_all_cases_passed_detail():
    """Verify that every individual test case matched expected outcome and severity."""
    report = run_benchmark(DATASET_PATH)
    for detail in report["results_detail"]:
        assert detail["passed"] is True, (
            f"Case {detail['case_id']} ({detail['rule_id']}) failed: "
            f"expected={detail['expected_outcome']}/{detail['expected_severity']}, "
            f"actual={detail['actual_outcome']}/{detail['actual_severity']}"
        )


def test_persisted_benchmark_report_validity():
    """Verify benchmark_report.json exists and contains correct schema."""
    assert REPORT_PATH.exists(), f"Benchmark report missing at {REPORT_PATH}"
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert "global_metrics" in report
    assert "per_rule_metrics" in report
    assert report["global_metrics"]["precision"] == 1.0
    assert report["global_metrics"]["recall"] == 1.0
