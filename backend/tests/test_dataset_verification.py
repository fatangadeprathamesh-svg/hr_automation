import os
import csv
import time
import pytest
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.master_hr import MasterUpload
from app.models.hr import AuditRun, AuditFlag, Employee
from app.services.master_import_service import MasterImportService
from app.rules.engine import AuditEngine


RULE_MAP_REVERSE = {
    "missing_punch": "MISSING_PUNCH",
    "hours_mismatch": "HOURS_MISMATCH",
    "unapproved_overtime": "OVERTIME_NO_APPROVAL",
    "pending_approvals": "PENDING_APPROVAL",
    "missing_receipt": "MISSING_RECEIPT",
    "duplicate_claim": "DUPLICATE_CLAIM",
    "over_limit_claim": "OVER_LIMIT_CLAIM",
    "leave_conflict": "LEAVE_CONFLICT",
}


def test_dataset_verification_and_precision_recall(db_session: Session):
    csv_path = Path("dataset/hr_audit_master.csv")
    gt_path = Path("dataset/issues_ground_truth.csv")

    assert csv_path.exists(), f"Missing dataset file: {csv_path}"
    assert gt_path.exists(), f"Missing ground truth file: {gt_path}"

    start_time = time.time()
    upload_id = "test_verification_batch"

    upload_record = MasterUpload(
        id=upload_id,
        filename="hr_audit_master.csv",
        sha256="test_sha256",
        uploaded_by="test_admin",
        status="queued",
        total_rows=0,
        accepted_rows=0,
        rejected_rows=0,
    )
    db_session.add(upload_record)
    db_session.commit()

    print("\n--- Starting Ingestion of hr_audit_master.csv ---")
    import_start = time.time()
    MasterImportService.process_upload_task(
        upload_id=upload_id,
        file_path=str(csv_path),
        actor_id="test_admin",
        actor_org="ORG_TEST",
        actor_role="hr_admin",
        db=db_session,
    )
    import_duration = time.time() - import_start
    print(f"Ingestion & initial evaluation completed in {import_duration:.2f} seconds.")

    # 1. Verify Alice Employee (EMP0001) in 2026-10
    alice_runs = db_session.query(AuditRun).filter(
        AuditRun.employee_id == "EMP0001",
        AuditRun.period == "2026-10"
    ).all()
    assert len(alice_runs) > 0, "No audit run found for EMP0001 in 2026-10"
    latest_alice_run = alice_runs[-1]

    alice_flags = db_session.query(AuditFlag).filter(
        AuditFlag.audit_run_id == latest_alice_run.audit_run_id,
        AuditFlag.outcome == "fail"
    ).all()

    print(f"\n--- Alice Employee (EMP0001) Findings in 2026-10 (Count: {len(alice_flags)}) ---")
    alice_findings_summary = []
    for f in alice_flags:
        rule_name = RULE_MAP_REVERSE.get(f.rule_id, f.rule_id.upper())
        event_date = f.evidence.get("event_date") or f.evidence.get("claim_date") or f.evidence.get("work_date")
        alice_findings_summary.append({
            "rule": rule_name,
            "record_id": f.record_id,
            "date": event_date,
            "severity": f.severity,
        })
        print(f"  - [{rule_name}] {f.record_id} on {event_date} (severity: {f.severity})")

    assert len(alice_flags) == 5, f"Expected exactly 5 findings for Alice in 2026-10, found {len(alice_flags)}"

    expected_alice_findings = {
        ("HOURS_MISMATCH", "TIM-031757", "2026-10-06"),
        ("OVERTIME_NO_APPROVAL", "ATT-031758", "2026-10-07"),
        ("MISSING_PUNCH", "ATT-031760", "2026-10-09"),
        ("MISSING_RECEIPT", "EXP-001561", "2026-10-15"),
        ("DUPLICATE_CLAIM", "EXP-001563", "2026-10-20"),
    }

    actual_alice_findings = {
        (f["rule"], f["record_id"], f["date"]) for f in alice_findings_summary
    }

    assert actual_alice_findings == expected_alice_findings, (
        f"Alice findings mismatch!\nExpected: {expected_alice_findings}\nActual: {actual_alice_findings}"
    )
    print(">>> ALICE EMP0001 FINDINGS VERIFIED EXACTLY (5 / 5 MATCH)")

    # 2. Precision & Recall Evaluation against issues_ground_truth.csv
    print("\n--- Evaluating Precision & Recall Across Full Dataset ---")
    gt_findings = set()
    gt_by_rule = {}
    with open(gt_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            r = row["rule"].strip()
            rec_id = row["record_id"].strip()
            emp_id = row["employee_id"].strip()
            key = (r, rec_id, emp_id)
            gt_findings.add(key)
            gt_by_rule[r] = gt_by_rule.get(r, 0) + 1

    all_flags = db_session.query(AuditFlag, AuditRun.employee_id).join(
        AuditRun, AuditFlag.audit_run_id == AuditRun.audit_run_id
    ).filter(AuditFlag.outcome == "fail").all()

    pred_findings = set()
    pred_by_rule = {}
    for flag, emp_id in all_flags:
        r_name = RULE_MAP_REVERSE.get(flag.rule_id, flag.rule_id.upper())
        rec_id = flag.record_id
        if rec_id:
            key = (r_name, rec_id, emp_id)
            pred_findings.add(key)
            pred_by_rule[r_name] = pred_by_rule.get(r_name, 0) + 1

    tp_total = len(pred_findings.intersection(gt_findings))
    fp_total = len(pred_findings - gt_findings)
    fn_total = len(gt_findings - pred_findings)

    overall_precision = tp_total / (tp_total + fp_total) if (tp_total + fp_total) > 0 else 0.0
    overall_recall = tp_total / (tp_total + fn_total) if (tp_total + fn_total) > 0 else 0.0
    overall_f1 = (
        2 * (overall_precision * overall_recall) / (overall_precision + overall_recall)
        if (overall_precision + overall_recall) > 0
        else 0.0
    )

    print(f"\nGround Truth Total Issues: {len(gt_findings)}")
    print(f"Predicted Total Issues:    {len(pred_findings)}")
    print(f"True Positives (TP):       {tp_total}")
    print(f"False Positives (FP):      {fp_total}")
    print(f"False Negatives (FN):      {fn_total}")
    print(f"Overall Precision:         {overall_precision * 100:.2f}%")
    print(f"Overall Recall:            {overall_recall * 100:.2f}%")
    print(f"Overall F1 Score:          {overall_f1 * 100:.2f}%\n")

    print(f"{'Rule Name':<24} | {'GT Count':<8} | {'Pred Count':<10} | {'Precision':<10} | {'Recall':<10} | {'F1 Score':<10}")
    print("-" * 80)
    for rule in sorted(gt_by_rule.keys()):
        rule_gt = {k for k in gt_findings if k[0] == rule}
        rule_pred = {k for k in pred_findings if k[0] == rule}
        tp = len(rule_pred.intersection(rule_gt))
        fp = len(rule_pred - rule_gt)
        fn = len(rule_gt - rule_pred)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        print(f"{rule:<24} | {len(rule_gt):<8} | {len(rule_pred):<10} | {prec * 100:>8.2f}% | {rec * 100:>8.2f}% | {f1 * 100:>8.2f}%")

    total_time = time.time() - start_time
    print(f"\nTotal verification completed in {total_time:.2f} seconds.")

    assert overall_precision >= 0.90, f"Precision {overall_precision:.2f} is below 90%"
    assert overall_recall >= 0.90, f"Recall {overall_recall:.2f} is below 90%"
