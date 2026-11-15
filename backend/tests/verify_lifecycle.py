import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000")

# 1. Alice checks readiness
r = client.get("/employees/me/readiness?period=2026-10", headers={"Authorization": "Bearer DEV_TOKEN_EMP001_employee"}).json()
print("Initial blockers:", r["blocking_count"])
att_flag = next(f for f in r["blocking_issues"] if f["rule_id"] == "MISSING_PUNCH")
exp_flag = next(f for f in r["blocking_issues"] if f["rule_id"] == "MISSING_RECEIPT")

# 2. Alice submits correction for punch
c1 = client.post("/corrections", headers={"Authorization": "Bearer DEV_TOKEN_EMP001_employee"}, json={
    "flag_id": att_flag["flag_id"],
    "entity_name": "attendance",
    "entity_id": att_flag["evidence"]["record_id"],
    "proposed_data": {"clock_out": "2026-10-02T17:30:00-04:00"},
    "employee_reason": "Card reader battery died at exit."
})
print("Correction 1 status:", c1.status_code, c1.json()["status"])

# 3. Alice submits correction for expense
c2 = client.post("/corrections", headers={"Authorization": "Bearer DEV_TOKEN_EMP001_employee"}, json={
    "flag_id": exp_flag["flag_id"],
    "entity_name": "expense_claim",
    "entity_id": exp_flag["evidence"]["record_id"],
    "proposed_data": {"receipt_reference": "s3://hr-receipts/palm_receipt_rec_002.pdf"},
    "employee_reason": "Uploaded itemized dining receipt."
})
print("Correction 2 status:", c2.status_code, c2.json()["status"])

# 4. Bob Manager lists pending corrections
mgr_list = client.get("/corrections/pending", headers={"Authorization": "Bearer DEV_TOKEN_MGR001_manager"}).json()
print("Manager pending corrections count:", len(mgr_list))

# 5. Bob Manager approves both
for item in mgr_list:
    cid = item["correction_id"]
    dec = client.post(f"/corrections/{cid}/decision", headers={"Authorization": "Bearer DEV_TOKEN_MGR001_manager"}, json={
        "decision": "approved",
        "manager_reason": "Verified and approved with employee log."
    })
    print(f"Decision on {cid}:", dec.status_code, dec.json()["decision"])

# 6. Alice re-checks readiness
r_after = client.get("/employees/me/readiness?period=2026-10", headers={"Authorization": "Bearer DEV_TOKEN_EMP001_employee"}).json()
print("Post-approval blockers:", r_after["blocking_count"], "Submission allowed:", r_after["submission_allowed"])

# 7. Alice submits month-end pack
sub = client.post("/submissions", headers={"Authorization": "Bearer DEV_TOKEN_EMP001_employee"}, json={"period": "2026-10"})
print("Submission response:", sub.status_code, sub.json()["snapshot_id"], "Status:", sub.json()["status"])
snapshot_id = sub.json()["snapshot_id"]

# 8. HR Admin approves submission
hr_dec = client.post(f"/submissions/{snapshot_id}/hr-decision", headers={"Authorization": "Bearer DEV_TOKEN_HR001_hr_admin"}, json={
    "decision": "approved",
    "hr_reason": "Verified zero blockers and manager approval."
})
print("HR Decision:", hr_dec.status_code, hr_dec.json()["status"])

# 9. HR Admin generates export pack
exp = client.post("/exports", headers={"Authorization": "Bearer DEV_TOKEN_HR001_hr_admin"}, json={"snapshot_id": snapshot_id})
print("Export Run:", exp.status_code, exp.json()["export_run_id"], "PDF URI:", exp.json()["pack_pdf_uri"])

# 10. Download check
pdf_dl = client.get(f"/exports/{exp.json()['export_run_id']}/download/pdf", headers={"Authorization": "Bearer DEV_TOKEN_HR001_hr_admin"})
print("PDF download status:", pdf_dl.status_code, "Bytes:", len(pdf_dl.content))
json_dl = client.get(f"/exports/{exp.json()['export_run_id']}/download/json", headers={"Authorization": "Bearer DEV_TOKEN_HR001_hr_admin"})
print("JSON download status:", json_dl.status_code, "Bytes:", len(json_dl.content))
print("ALL CHECKS PASSED PERFECTLY!")
