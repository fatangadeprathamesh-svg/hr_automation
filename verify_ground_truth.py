#!/usr/bin/env python3
"""
verify_ground_truth.py - Deterministic HR Self-Audit Ground Truth Verification

Usage:
    python verify_ground_truth.py [--csv <master_csv>] [--truth <ground_truth_csv>] [--period 2026-10]
    python verify_ground_truth.py --benchmark
    python verify_ground_truth.py (runs self-verification if no arguments supplied)

Measures:
  1. CSV import throughput and timing
  2. Deterministic audit engine evaluation timing
  3. Per-rule Precision, Recall, F1-Score, and detailed mismatch reporting
"""

import os
import sys
import time
import json
import csv
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any, List, Set, Tuple, Optional

# Ensure backend app is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal, engine, Base
from app.models.master_hr import MasterUpload, MasterHRRecord
from app.models.hr import Employee, AuditFlag, AuditRun, AuditEvent
from app.services.master_import_service import MasterImportService
from app.rules.engine import AuditEngine


# Normalization map for rule names
RULE_NAME_MAP = {
    "MISSING_PUNCH": "MISSING_PUNCH",
    "HOURS_MISMATCH": "HOURS_MISMATCH",
    "MISSING_RECEIPT": "MISSING_RECEIPT",
    "DUPLICATE_CLAIM": "DUPLICATE_CLAIM",
    "OVER_LIMIT_CLAIM": "OVER_LIMIT_CLAIM",
    "LEAVE_CONFLICT": "LEAVE_CONFLICT",
    "OVERTIME_NO_APPROVAL": "OVERTIME_NO_APPROVAL",
    "UNAPPROVED_OVERTIME": "OVERTIME_NO_APPROVAL",
    "PENDING_APPROVAL": "PENDING_APPROVAL",
    "PENDING_APPROVALS": "PENDING_APPROVAL",
    "EXPIRING_DOCUMENTS": "EXPIRING_DOCUMENTS",
}


def normalize_rule_id(raw_id: str) -> str:
    cleaned = (raw_id or "").strip().upper().replace(" ", "_")
    return RULE_NAME_MAP.get(cleaned, cleaned)


def run_benchmark_dataset():
    """Runs the 9-rule benchmark against evaluation/ground_truth_dataset.json."""
    dataset_path = SCRIPT_DIR / "evaluation" / "ground_truth_dataset.json"
    if not dataset_path.exists():
        print(f"[!] Benchmark dataset not found at {dataset_path}")
        return

    from evaluation.evaluate_rules import run_benchmark
    print("=" * 70)
    print("BENCHMARK EVALUATION: evaluation/ground_truth_dataset.json")
    print("=" * 70)
    t0 = time.time()
    report = run_benchmark(dataset_path)
    elapsed = time.time() - t0

    gm = report.get("global_metrics", {})
    print(f"Total Cases:     {gm.get('total_cases', 0)}")
    print(f"Passed:          {gm.get('tp', 0) + gm.get('tn', 0)}")
    print(f"False Positives: {gm.get('fp', 0)}")
    print(f"False Negatives: {gm.get('fn', 0)}")
    print(f"Precision:       {gm.get('precision', 0.0) * 100:.1f}%")
    print(f"Recall:          {gm.get('recall', 0.0) * 100:.1f}%")
    print(f"F1-Score:        {gm.get('f1_score', 0.0) * 100:.1f}%")
    print(f"Accuracy:        {gm.get('accuracy', 0.0) * 100:.1f}%")
    print(f"Data Health Acc: {gm.get('data_health_accuracy', 0.0) * 100:.1f}%")
    print(f"Benchmark Time:  {elapsed:.3f}s")
    print("-" * 70)
    print(f"{'Rule ID':<24} | {'Cases':<6} | {'Precision':<10} | {'Recall':<10} | {'F1':<8}")
    print("-" * 70)
    for r_id, m in report.get("per_rule_metrics", {}).items():
        print(f"{r_id:<24} | {m.get('total_cases', 0):<6} | {m.get('precision', 0.0)*100:>8.1f}% | {m.get('recall', 0.0)*100:>8.1f}% | {m.get('f1_score', 0.0)*100:>6.1f}%")
    print("=" * 70)


def import_csv_timed(csv_path: Path, db) -> Tuple[float, int, int]:
    """Imports a master CSV file and maps records into operational audit tables."""
    print(f"[*] Importing master CSV: {csv_path.name}...")
    t0 = time.time()

    # Create MasterUpload record
    upload_id = f"upload_{int(t0)}"
    upload = MasterUpload(
        id=upload_id,
        filename=csv_path.name,
        file_size_bytes=csv_path.stat().st_size,
        file_hash="manual_verify",
        status="processing",
        total_rows=0,
        accepted_rows=0,
        rejected_rows=0,
    )
    db.add(upload)
    db.commit()

    rej_path = SCRIPT_DIR / "temp_uploads" / f"rejected_{upload_id}.csv"
    rej_path.parent.mkdir(parents=True, exist_ok=True)

    MasterImportService.process_upload_task(
        upload_id=upload_id,
        file_path=str(csv_path),
        rejected_file_path=str(rej_path),
        delimiter=",",
        actor_user_id="verifier",
        actor_name="Ground Truth Verifier",
    )

    db.refresh(upload)
    elapsed = time.time() - t0

    print(f"[✓] Import completed in {elapsed:.3f}s: "
          f"{upload.accepted_rows} accepted, {upload.rejected_rows} rejected, "
          f"{upload.total_rows} total rows.")
    return elapsed, upload.accepted_rows, upload.rejected_rows


def evaluate_audit_timed(db, period: str) -> Tuple[float, int, int]:
    """Runs the deterministic rules engine across all employees and records timing."""
    print(f"[*] Running deterministic audit evaluation for period: {period}...")
    t0 = time.time()
    engine = AuditEngine()
    result = engine.evaluate_all_employees(db, period=period)
    elapsed = time.time() - t0

    emp_count = result.get("employees_evaluated", 0)
    flag_count = result.get("total_flags", 0)
    print(f"[✓] Evaluation completed in {elapsed:.3f}s: "
          f"{emp_count} employees evaluated, {flag_count} total audit findings.")
    return elapsed, emp_count, flag_count


def load_ground_truth(truth_path: Path) -> List[Dict[str, Any]]:
    """Loads ground truth from CSV or JSON."""
    truth_items = []
    if truth_path.suffix.lower() == ".json":
        with open(truth_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                truth_items = data
            elif isinstance(data, dict):
                truth_items = data.get("cases") or data.get("findings") or data.get("flags") or []
    else:
        with open(truth_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                truth_items.append(row)
    return truth_items


def compare_ground_truth(actual_flags: List[AuditFlag], truth_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compares actual DB flags with ground truth findings per rule.
    Computes TP, FP, FN, Precision, Recall, and F1.
    """
    # Group actual flags by rule_id
    actual_by_rule = defaultdict(set)
    actual_details = {}
    for flag in actual_flags:
        norm_r = normalize_rule_id(flag.rule_id)
        # Unique identifier for the finding: prefer record_id, else (employee_id, date)
        evidence = flag.evidence or {}
        rec_id = flag.record_id or evidence.get("record_id") or evidence.get("source_record_id")
        emp_id = flag.employee_id
        date_val = str(evidence.get("work_date") or evidence.get("claim_date") or evidence.get("event_date") or "")
        key = (emp_id, rec_id) if rec_id else (emp_id, date_val)
        actual_by_rule[norm_r].add(key)
        actual_details[(norm_r, key)] = {
            "flag_id": flag.flag_id,
            "rule_id": norm_r,
            "employee_id": emp_id,
            "record_id": rec_id,
            "severity": flag.severity,
            "description": flag.description,
        }

    # Group truth items by rule_id
    truth_by_rule = defaultdict(set)
    truth_details = {}
    for item in truth_items:
        # Check rule name column
        raw_r = item.get("rule_id") or item.get("rule") or item.get("policy_rule") or item.get("flag_type") or ""
        norm_r = normalize_rule_id(raw_r)
        emp_id = (item.get("employee_id") or item.get("emp_id") or "").strip()
        rec_id = (item.get("record_id") or item.get("source_record_id") or item.get("entity_id") or "").strip()
        date_val = (item.get("event_date") or item.get("work_date") or item.get("claim_date") or item.get("date") or "").strip()
        key = (emp_id, rec_id) if rec_id else (emp_id, date_val)
        truth_by_rule[norm_r].add(key)
        truth_details[(norm_r, key)] = item

    all_rules = sorted(set(list(actual_by_rule.keys()) + list(truth_by_rule.keys())))

    per_rule_stats = {}
    total_tp = 0
    total_fp = 0
    total_fn = 0

    mismatches = []

    for r in all_rules:
        actual_set = actual_by_rule.get(r, set())
        truth_set = truth_by_rule.get(r, set())

        tp_set = actual_set.intersection(truth_set)
        fp_set = actual_set.difference(truth_set)
        fn_set = truth_set.difference(actual_set)

        tp = len(tp_set)
        fp = len(fp_set)
        fn = len(fn_set)

        total_tp += tp
        total_fp += fp
        total_fn += fn

        prec = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
        rec = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if fp == 0 else 0.0)
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        per_rule_stats[r] = {
            "expected": len(truth_set),
            "actual": len(actual_set),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": prec,
            "recall": rec,
            "f1": f1,
        }

        # Collect mismatch details
        for fp_key in fp_set:
            mismatches.append({
                "type": "FALSE_POSITIVE (Unexpected)",
                "rule_id": r,
                "key": fp_key,
                "detail": actual_details.get((r, fp_key)),
            })
        for fn_key in fn_set:
            mismatches.append({
                "type": "FALSE_NEGATIVE (Missed)",
                "rule_id": r,
                "key": fn_key,
                "detail": truth_details.get((r, fn_key)),
            })

    global_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 1.0
    global_rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0
    global_f1 = (2 * global_prec * global_rec) / (global_prec + global_rec) if (global_prec + global_rec) > 0 else 0.0

    return {
        "per_rule": per_rule_stats,
        "global": {
            "total_tp": total_tp,
            "total_fp": total_fp,
            "total_fn": total_fn,
            "precision": global_prec,
            "recall": global_rec,
            "f1": global_f1,
        },
        "mismatches": mismatches,
    }


def main():
    parser = argparse.ArgumentParser(description="Deterministic HR Self-Audit Ground Truth Verification")
    parser.add_argument("--csv", type=str, help="Path to master CSV file")
    parser.add_argument("--truth", type=str, help="Path to ground truth findings CSV or JSON")
    parser.add_argument("--period", type=str, default="2026-10", help="Audit period (e.g. 2026-10)")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark suite against evaluation dataset")
    args = parser.parse_args()

    print("=" * 80)
    print("   HR SELF-AUDIT ASSISTANT - GROUND TRUTH VERIFICATION & BENCHMARK")
    print("=" * 80)

    # 1. Benchmark evaluation
    if args.benchmark or (not args.csv and not args.truth):
        run_benchmark_dataset()

    db = SessionLocal()

    import_time = 0.0
    eval_time = 0.0

    try:
        # 2. CSV Import
        if args.csv:
            csv_path = Path(args.csv)
            if not csv_path.exists():
                print(f"[!] Error: CSV file not found at {csv_path}")
                sys.exit(1)
            import_time, accepted, rejected = import_csv_timed(csv_path, db)

        # 3. Audit Engine Evaluation
        eval_time, emp_count, flag_count = evaluate_audit_timed(db, args.period)

        # 4. Ground Truth Comparison
        if args.truth:
            truth_path = Path(args.truth)
            if not truth_path.exists():
                print(f"[!] Error: Ground truth file not found at {truth_path}")
                sys.exit(1)

            print(f"[*] Loading ground truth from {truth_path.name}...")
            truth_items = load_ground_truth(truth_path)
            print(f"[✓] Loaded {len(truth_items)} ground truth entries.")

            actual_flags = db.query(AuditFlag).filter(AuditFlag.period == args.period).all()
            print(f"[*] Comparing {len(actual_flags)} actual flags with ground truth...")

            results = compare_ground_truth(actual_flags, truth_items)

            print("\n" + "=" * 80)
            print("GROUND TRUTH VERIFICATION REPORT")
            print("=" * 80)
            header = f"{'Rule ID':<22} | {'Exp':<5} | {'Act':<5} | {'TP':<4} | {'FP':<4} | {'FN':<4} | {'Prec':<7} | {'Recall':<7} | {'F1':<6}"
            print(header)
            print("-" * 80)

            for r, stats in results["per_rule"].items():
                print(f"{r:<22} | {stats['expected']:<5} | {stats['actual']:<5} | {stats['tp']:<4} | {stats['fp']:<4} | {stats['fn']:<4} | {stats['precision']*100:>5.1f}% | {stats['recall']*100:>5.1f}% | {stats['f1']*100:>5.1f}%")

            g = results["global"]
            print("-" * 80)
            print(f"{'OVERALL':<22} | {'-':<5} | {'-':<5} | {g['total_tp']:<4} | {g['total_fp']:<4} | {g['total_fn']:<4} | {g['precision']*100:>5.1f}% | {g['recall']*100:>5.1f}% | {g['f1']*100:>5.1f}%")
            print("=" * 80)

            if results["mismatches"]:
                print(f"\n[!] MISMATCHES DETECTED ({len(results['mismatches'])} total):")
                for idx, m in enumerate(results["mismatches"][:15], 1):
                    print(f"  {idx}. {m['type']} - Rule: {m['rule_id']}, Key: {m['key']}")
                    print(f"     Details: {m['detail']}")
                if len(results["mismatches"]) > 15:
                    print(f"     ... and {len(results['mismatches']) - 15} more.")
            else:
                print("\n[✓] PERFECT 100% MATCH: Zero False Positives and Zero False Negatives!")

        print("\n" + "=" * 80)
        print("PERFORMANCE & EXECUTION SUMMARY")
        print("=" * 80)
        if args.csv:
            print(f"  - Master CSV Import Time:       {import_time:.3f}s")
        print(f"  - Rules Engine Evaluation Time: {eval_time:.3f}s ({emp_count} employees)")
        print(f"  - Total Audit Findings Stored:  {flag_count} flags")
        print("=" * 80 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
