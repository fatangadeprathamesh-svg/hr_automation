import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi import HTTPException, Response
from app.database import SessionLocal
from app.auth.security import ActorIdentity
from app.api.audit import get_my_readiness, get_manager_metrics, get_hr_metrics, list_audit_periods
from app.api.master_uploads import get_sync_status, get_master_stats
from app.api.duties import get_duty_detail


def run_checks():
    db = SessionLocal()
    actor_emp = ActorIdentity(actor_id='EMP0001', organization_id='default', role='employee', email='alice@company.com')
    actor_mgr = ActorIdentity(actor_id='EMP0002', organization_id='default', role='manager', email='bob@company.com')
    actor_hr = ActorIdentity(actor_id='EMP0003', organization_id='default', role='hr_admin', email='carol@company.com')
    actor_ic = ActorIdentity(actor_id='EMP0004', organization_id='default', role='ic_member', email='irene@company.com')

    print("=== 1. Testing Employee Readiness (Alice EMP0001) ===")
    emp_res = get_my_readiness('2026-10', actor_emp, db)
    assert emp_res['employee_id'] == 'EMP0001', f"Expected EMP0001, got {emp_res['employee_id']}"
    assert emp_res['readiness_score'] == 90.9, f"Expected 90.9, got {emp_res['readiness_score']}"
    assert emp_res['readiness_percentage'] == 90.9, f"Expected 90.9, got {emp_res['readiness_percentage']}"
    assert len(emp_res['flags']) == 7, f"Expected 7 flags, got {len(emp_res['flags'])}"
    assert emp_res['has_evaluated'] is True
    assert emp_res['has_data'] is True
    assert emp_res['blocking_count'] == 5
    assert emp_res['warning_count'] == 0
    print(f"   [PASS] Alice Employee is EMP0001: readiness={emp_res['readiness_score']}%, blockers={emp_res['blocking_count']}, flags={len(emp_res['flags'])}")

    print("=== 2. Testing Manager Metrics (Bob EMP0002) ===")
    mgr_res = get_manager_metrics('2026-10', actor_mgr, db)
    assert mgr_res['total_team_members'] == 24, f"Expected 24 team members, got {mgr_res['total_team_members']}"
    assert mgr_res['average_readiness'] == 96.1, f"Expected 96.1, got {mgr_res['average_readiness']}"
    assert mgr_res['open_blockers'] == 30, f"Expected 30 blockers, got {mgr_res['open_blockers']}"
    print(f"   [PASS] Bob Manager: team={mgr_res['total_team_members']}, avg_readiness={mgr_res['average_readiness']}%, open_blockers={mgr_res['open_blockers']}")

    print("=== 3. Testing HR Metrics (Carol EMP0003) ===")
    hr_res = get_hr_metrics('2026-10', actor_hr, db)
    assert hr_res['total_employees'] == 304, f"Expected 304, got {hr_res['total_employees']}"
    assert hr_res['average_readiness'] == 95.1, f"Expected 95.1, got {hr_res['average_readiness']}"
    assert hr_res['open_blockers'] == 332, f"Expected 332, got {hr_res['open_blockers']}"
    print(f"   [PASS] Carol HR Admin: total_employees={hr_res['total_employees']}, avg_readiness={hr_res['average_readiness']}%, open_blockers={hr_res['open_blockers']}")

    print("=== 4. Testing Role Sync Status ===")
    resp = Response()
    s_emp = get_sync_status(resp, actor_emp, db)
    assert s_emp['role_scope'] == 'employee'
    assert s_emp['total_findings'] == 8
    s_mgr = get_sync_status(resp, actor_mgr, db)
    assert s_mgr['role_scope'] == 'manager'
    assert s_mgr['total_findings'] == 149
    s_hr = get_sync_status(resp, actor_hr, db)
    assert s_hr['role_scope'] == 'hr_admin'
    print(f"   [PASS] Sync status: employee={s_emp['total_findings']} findings, manager={s_mgr['total_findings']} findings, hr={s_hr['role_scope']}")

    print("=== 5. Testing Audit Periods Fast-Path & Caching ===")
    periods_res = list_audit_periods(actor_emp, db)
    assert '2026-10' in periods_res['periods']
    assert periods_res['default_period'] == '2026-10'
    print(f"   [PASS] Periods: {periods_res['periods']}")

    print("=== 6. Testing IC Member Isolation ===")
    posh = get_duty_detail('posh', actor_ic, db)
    assert posh['config']['key'] == 'posh'
    print("   [PASS] Irene IC Member can access POSH duty")
    try:
        get_duty_detail('attendance_leave', actor_ic, db)
        assert False, "Should have thrown 403"
    except HTTPException as e:
        assert e.status_code == 403
        print("   [PASS] Irene IC Member rejected on attendance_leave with 403 Forbidden")

    db.close()
    print("\n>>> ALL SYSTEM VERIFICATIONS PASSED CLEANLY! <<<")


if __name__ == "__main__":
    run_checks()
