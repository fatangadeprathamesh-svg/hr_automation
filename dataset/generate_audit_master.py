"""Synthetic AUDIT-focused master CSV (61 columns) for the HR Self-Audit app.
Same 55 columns as hr_merged_master.csv + 6 new optional columns:
email, project_code, amount, expense_category, receipt_attached, overtime_approved
Record types: employee_profile, attendance, timesheet, expense, leave_request, leave_balance
"""
import csv, random, calendar, argparse
from datetime import date, datetime, timedelta
p = argparse.ArgumentParser()
p.add_argument("--employees", type=int, default=300)
p.add_argument("--start", default="2026-05")
p.add_argument("--months", type=int, default=6)
p.add_argument("--seed", type=int, default=7)
p.add_argument("--out", default="hr_audit_master.csv")
p.add_argument("--truth", default="issues_ground_truth.csv")
a = p.parse_args(); random.seed(a.seed)

BASE = ["record_id","record_type","source_file","employee_id","applicant_id","employee_name","first_name","last_name","department","position","division","business_unit","branch_location","manager","employment_type","gender","age","dob","marital_status","state","education","hire_date","exit_date","employee_status","performance_score","performance_rating","monthly_income","years_experience","salary_hike_pct","event_date","start_date","end_date","applied_date","status","category","reason","days","clock_in","clock_out","hours_total","hours_scheduled","break_minutes","leave_entitlement","leave_taken_so_far","leave_remaining","engagement_score","satisfaction_score","work_life_balance_score","training_program","training_outcome","trainer","training_location","training_cost","desired_salary","country"]
NEW = ["email","project_code","amount","expense_category","receipt_attached","overtime_approved"]
COLS = BASE + NEW
assert len(BASE) == 55
out = open(a.out, "w", newline="", encoding="utf-8"); w = csv.DictWriter(out, fieldnames=COLS); w.writeheader()
truth = []
cnt = {}
PFX = {"employee_profile":"PRF","attendance":"ATT","timesheet":"TIM","expense":"EXP","leave_request":"LRQ","leave_balance":"LBL"}
def rid(t):
    cnt[t] = cnt.get(t, 0) + 1; return f"{PFX[t]}-{cnt[t]:06d}"
def row(t, **kw):
    r = {c: "" for c in COLS}; r["record_type"] = t; r["source_file"] = "hr_audit_master.csv"; r["record_id"] = rid(t); r.update(kw); w.writerow(r); return r["record_id"]
def flag(rule, record_id, emp, ev):
    truth.append((rule, record_id, emp, ev))

first = ["Aarav","Vihaan","Ananya","Diya","Rohan","Priya","Arjun","Sneha","Kabir","Isha","Meera","Rahul","Pooja","Siddharth","Neha","Karan","Divya","Nikhil","Sana","Varun"]
last = ["Sharma","Patil","Kulkarni","Deshmukh","Iyer","Reddy","Khan","Singh","Joshi","Gupta","Mehta","Nair","Chen","Bose","Shah"]
depts = ["Engineering","Finance","Sales","Support","Operations","Marketing","Legal","HR"]
states = ["Maharashtra","Karnataka","Gujarat","Delhi"]
personas = [("Alice Employee","alice@company.com","Engineering"),("Bob Manager","bob@company.com","Engineering"),("Carol HR","carol@company.com","HR"),("Irene IC Member","irene@company.com","Legal")]
emps = []
for i in range(1, a.employees + 1):
    eid = f"EMP{i:04d}"
    if i <= len(personas): name, email, dept = personas[i-1]
    else:
        name = f"{random.choice(first)} {random.choice(last)}"; email = f"{eid.lower()}@company.com"; dept = random.choice(depts)
    emps.append(dict(id=eid, name=name, email=email, dept=dept, state=random.choice(states)))
mgr_names = ["Bob Manager"] + [f"{random.choice(first)} {random.choice(last)} (Mgr)" for _ in range(11)]
for i, e in enumerate(emps):
    if e["name"] == "Bob Manager": e["mgr"] = "Carol HR"
    elif i < 25 and i != 2: e["mgr"] = "Bob Manager"
    else: e["mgr"] = random.choice(mgr_names[1:])
    if e["name"] == "Alice Employee": e["mgr"] = "Bob Manager"
    row("employee_profile", employee_id=e["id"], employee_name=e["name"], department=e["dept"], position="Associate",
        manager=e["mgr"], employment_type="Full-time", state=e["state"], hire_date=(date(2019,1,1)+timedelta(days=random.randint(0,2000))).isoformat(),
        employee_status="Active", email=e["email"], branch_location=e["state"])

y, m = map(int, a.start.split("-"))
months = []
for k in range(a.months):
    mm = m + k; yy = y + (mm-1)//12; mm = (mm-1)%12 + 1; months.append((yy, mm))
holidays = {date(2026,8,15), date(2026,10,2), date(2026,5,1)}
projects = ["PRJ-ALPHA","PRJ-BETA","PRJ-GAMMA","INTERNAL"]
LIM = {"Meals":60,"Travel":300,"Software":150,"Training":400,"Fuel":80}
for mi, (yy, mm) in enumerate(months):
    rate = 0.07 - 0.035 * mi / max(1, len(months)-1)      # improving trend 7% -> 3.5%
    nd = calendar.monthrange(yy, mm)[1]
    days = [date(yy, mm, d) for d in range(1, nd+1)]
    wd = [d for d in days if d.weekday() < 5 and d not in holidays]
    leave_days = {}
    for e in emps:
        if random.random() < 0.30:
            s = random.choice(wd); L = random.randint(1, 3)
            dd = [s + timedelta(days=k) for k in range(L) if (s + timedelta(days=k)) in wd]
            if not dd: continue
            status = random.choices(["Approved","Pending"], [88, 12])[0]
            lid = row("leave_request", employee_id=e["id"], employee_name=e["name"], department=e["dept"], manager=e["mgr"],
                category=random.choice(["Casual Leave","Sick Leave","Earned Leave"]), start_date=dd[0].isoformat(), end_date=dd[-1].isoformat(),
                days=len(dd), status=status, applied_date=(dd[0]-timedelta(days=random.randint(1,10))).isoformat(), event_date=dd[0].isoformat())
            if status == "Approved":
                for d in dd: leave_days[(e["id"], d)] = lid
    for e in emps:
        is_alice = e["name"] == "Alice Employee"
        forced = ["MISSING_PUNCH","HOURS_MISMATCH","MISSING_RECEIPT","OVERTIME_NO_APPROVAL"] if (is_alice and (yy, mm) == months[-1]) else []
        for d in wd:
            lv = leave_days.get((e["id"], d))
            if lv and random.random() > 0.01:
                continue
            pin = datetime.combine(d, datetime.min.time()) + timedelta(hours=9, minutes=random.randint(-15, 40))
            hrs = round(min(max(random.gauss(8.4, 0.5), 6.5), 9.4), 2)
            pout = pin + timedelta(hours=hrs)
            cin, cout, hw, ot = pin.strftime("%H:%M"), pout.strftime("%H:%M"), hrs, ""
            status = "Late" if pin.hour*60+pin.minute > 555 else "Present"
            issues = []
            if lv:
                issues.append("LEAVE_CONFLICT")
            elif forced and d.weekday() == 4 and "MISSING_PUNCH" in forced: issues.append("MISSING_PUNCH"); forced.remove("MISSING_PUNCH")
            elif forced and "OVERTIME_NO_APPROVAL" in forced and d.weekday() == 2: issues.append("OVERTIME_NO_APPROVAL"); forced.remove("OVERTIME_NO_APPROVAL")
            elif forced and "HOURS_MISMATCH" in forced and d.weekday() == 1: issues.append("HOURS_MISMATCH"); forced.remove("HOURS_MISMATCH")
            elif random.random() < rate * 0.9:
                issues.append(random.choices(["MISSING_PUNCH","OVERTIME_NO_APPROVAL","HOURS_MISMATCH"], [45, 25, 30])[0])
            ts_hours = round(min(hrs, 8) + random.choice([0, 0, 0.25, -0.25]), 2)
            if "MISSING_PUNCH" in issues:
                cout, hw = "", ""
                if d.weekday() != 4 and random.random() < .5: pass
            if "OVERTIME_NO_APPROVAL" in issues:
                hrs = round(random.uniform(10, 12), 2); pout = pin + timedelta(hours=hrs); cout = pout.strftime("%H:%M"); hw = hrs; ot = "N"; ts_hours = 8
            elif hw != "" and hw > 9.5: ot = "Y"
            if "HOURS_MISMATCH" in issues: ts_hours = round(hrs + random.choice([-1, 1]) * random.uniform(0.9, 2.5), 2)
            rec = row("attendance", employee_id=e["id"], employee_name=e["name"], department=e["dept"], manager=e["mgr"], event_date=d.isoformat(),
                clock_in=cin, clock_out=cout, hours_total=hw, hours_scheduled=8, break_minutes=random.choice([30,45,60]), status=status, overtime_approved=ot, branch_location=e["state"])
            for rule in issues:
                flag(rule, rec if rule != "HOURS_MISMATCH" else "TIM-pending", e["id"], d.isoformat())
            tstat = "Approved"
            if (yy, mm) == months[-1] and random.random() < 0.02: tstat = "Unapproved"; 
            trec = row("timesheet", employee_id=e["id"], employee_name=e["name"], department=e["dept"], event_date=d.isoformat(), hours_total=ts_hours,
                project_code=random.choice(projects), status=tstat)
            if "HOURS_MISMATCH" in issues: truth[-1] = ("HOURS_MISMATCH", trec, e["id"], d.isoformat())
            if tstat == "Unapproved": flag("PENDING_APPROVAL", trec, e["id"], d.isoformat())
        # expenses
        n = random.choices([0,1,2,3],[40,30,20,10])[0]
        made = []
        for _ in range(n + (2 if forced else 0)):
            cat = random.choice(list(LIM)); d = random.choice(wd)
            amt = round(random.uniform(0.1, 0.9) * LIM[cat], 2); rc = random.choices(["Y","N"],[93,7])[0]
            rule = None
            if "MISSING_RECEIPT" in forced: amt = max(amt, 40.0); rc = "N"; rule = "MISSING_RECEIPT"; forced.remove("MISSING_RECEIPT")
            elif random.random() < rate:
                rule = random.choice(["MISSING_RECEIPT","OVER_LIMIT_CLAIM","DUPLICATE_CLAIM"])
                if rule == "MISSING_RECEIPT": amt = max(amt, 30.0); rc = "N"
                elif rule == "OVER_LIMIT_CLAIM": amt = round(LIM[cat] * random.uniform(1.2, 2.5), 2); rc = "Y"
                elif rule == "DUPLICATE_CLAIM": rc = "Y"; made.append((cat, d, amt, rc))
            if rule is None and rc == "N" and amt > 25: rc = "Y"   # keep non-flagged rows clean
            xid = row("expense", employee_id=e["id"], employee_name=e["name"], department=e["dept"], manager=e["mgr"], event_date=d.isoformat(),
                expense_category=cat, amount=amt, receipt_attached=rc, status=random.choice(["Submitted","Approved"]), reason=f"{cat} expense")
            if rule and rule != "DUPLICATE_CLAIM": flag(rule, xid, e["id"], d.isoformat())
            if rule == "DUPLICATE_CLAIM":
                x2 = row("expense", employee_id=e["id"], employee_name=e["name"], department=e["dept"], manager=e["mgr"], event_date=d.isoformat(),
                    expense_category=cat, amount=amt, receipt_attached=rc, status="Submitted", reason=f"{cat} expense")
                flag("DUPLICATE_CLAIM", x2, e["id"], d.isoformat())
for e in emps:
    ent = 24; taken = random.randint(0, 14)
    row("leave_balance", employee_id=e["id"], employee_name=e["name"], department=e["dept"], leave_entitlement=ent, leave_taken_so_far=taken, leave_remaining=ent-taken, category="Annual Leave")
out.close()
with open(a.truth, "w", newline="", encoding="utf-8") as f:
    t = csv.writer(f); t.writerow(["rule","record_id","employee_id","event_date"]); t.writerows(truth)
print(cnt, "truth rows:", len(truth))
