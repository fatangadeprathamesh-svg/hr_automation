#!/usr/bin/env python3
"""
Stress Testing & Synthetic Master HR CSV Generator.
Generates large scale (e.g. 13k to 500k+ rows) master HR CSV with 55 columns
and benchmarks ingestion throughput using the streaming MasterImportService.
"""

import os
import sys
import csv
import time
import argparse
import random
from datetime import date, timedelta
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal, Base, engine
from app.models.master_hr import MasterUpload, MasterHRRecord
from app.services.master_import_service import MasterImportService, COLUMNS, VALID_RECORD_TYPES

FIRST_NAMES = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen", "Elena", "Carlos", "Renée", "François", "O'Connor", "D'Souza"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "O'Neill", "St. Pierre"]
DEPARTMENTS = ["Engineering", "Product", "Operations", "Sales", "Marketing", "Finance", "Human Resources", "Legal", "Customer Support"]
POSITIONS = ["Software Engineer", "Senior Developer", "Product Manager", "Operations Analyst", "Account Executive", "Marketing Specialist", "Financial Analyst", "HR Specialist", "Support Lead"]
DIVISIONS = ["Commercial", "Consumer", "Enterprise", "Corporate Functions", "Digital Solutions"]
BRANCHES = ["New York", "San Francisco", "Chicago", "Austin", "London", "Toronto", "Sydney", "Singapore"]
MANAGERS = ["Bob Manager", "Dan Operations Manager", "Elena Product Manager", "Carol HR Admin"]
TRAINING_PROGS = ["Security Awareness 2026", "Leadership Essentials", "Data Privacy & GDPR", "Agile Fundamentals", "Cloud Architecture 101"]


def generate_stress_csv(output_path: Path, num_rows: int = 500000):
    """Generates a synthetic master HR CSV with num_rows in UTF-8."""
    print(f"Generating synthetic master HR CSV with {num_rows:,} rows at: {output_path}")
    start_t = time.time()

    record_types = [
        "employee_profile",
        "leave_request",
        "leave_balance",
        "timesheet",
        "training",
        "engagement_survey",
        "applicant",
    ]
    weights = [0.20, 0.25, 0.15, 0.25, 0.05, 0.05, 0.05]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()

        batch = []
        batch_size = 10000

        for i in range(1, num_rows + 1):
            rec_type = random.choices(record_types, weights=weights)[0]
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            full_name = f"{first_name} {last_name}"
            emp_num = (i % 10000) + 1
            # Two styles of employee ID: "EMP0001" and "1001"
            emp_id = f"EMP{emp_num:04d}" if emp_num % 2 == 0 else str(1000 + emp_num)
            dept = random.choice(DEPARTMENTS)
            event_d = date(2026, 10, (i % 28) + 1)
            start_d = event_d
            end_d = start_d + timedelta(days=random.randint(0, 3))

            row = {c: "" for c in COLUMNS}
            row["record_id"] = f"MHR-{i:08d}"
            row["record_type"] = rec_type
            row["source_file"] = output_path.name
            row["department"] = dept
            row["position"] = random.choice(POSITIONS)
            row["division"] = random.choice(DIVISIONS)
            row["branch_location"] = random.choice(BRANCHES)
            row["manager"] = random.choice(MANAGERS)
            row["country"] = "United States"

            if rec_type == "employee_profile":
                row["employee_id"] = emp_id
                row["employee_name"] = full_name
                row["first_name"] = first_name
                row["last_name"] = last_name
                row["employment_type"] = "Full-Time"
                row["hire_date"] = "2024-03-01"
                row["monthly_income"] = str(random.randint(4500, 15000))
                row["age"] = str(random.randint(22, 62))
                row["dob"] = "1990-06-15"
                row["employee_status"] = "Active"

            elif rec_type == "leave_request":
                row["employee_id"] = emp_id
                row["employee_name"] = full_name
                row["start_date"] = start_d.isoformat()
                row["end_date"] = end_d.isoformat()
                row["days"] = str((end_d - start_d).days + 1)
                row["category"] = random.choice(["annual", "sick", "personal"])
                row["status"] = "approved"

            elif rec_type == "leave_balance":
                row["employee_id"] = emp_id
                row["employee_name"] = full_name
                row["leave_entitlement"] = "25.0"
                row["leave_taken_so_far"] = str(random.randint(2, 18))
                row["leave_remaining"] = "15.0"

            elif rec_type == "timesheet":
                # Timesheet rows have NO employee_id (name only)
                row["employee_id"] = ""
                row["employee_name"] = full_name
                row["event_date"] = event_d.isoformat()
                row["clock_in"] = "09:00"
                row["clock_out"] = "17:30"
                row["hours_total"] = "8.0"
                row["hours_scheduled"] = "8.0"
                row["status"] = "approved" if i % 10 != 0 else "pending"

            elif rec_type == "training":
                row["employee_id"] = emp_id
                row["employee_name"] = full_name
                row["training_program"] = random.choice(TRAINING_PROGS)
                row["training_outcome"] = "Completed"
                row["training_cost"] = str(random.choice([150.0, 300.0, 500.0]))

            elif rec_type == "engagement_survey":
                row["employee_id"] = emp_id
                row["employee_name"] = full_name
                row["engagement_score"] = str(random.randint(7, 10))
                row["satisfaction_score"] = str(random.randint(7, 10))
                row["work_life_balance_score"] = str(random.randint(6, 10))

            elif rec_type == "applicant":
                row["applicant_id"] = f"APP-{i:06d}"
                row["employee_name"] = full_name
                row["applied_date"] = "2026-09-20"
                row["status"] = "Interviewing"
                row["desired_salary"] = "95000"

            batch.append(row)
            if len(batch) >= batch_size:
                writer.writerows(batch)
                batch.clear()
                if i % 100000 == 0:
                    print(f"  ... generated {i:,} / {num_rows:,} rows")

        if batch:
            writer.writerows(batch)
            batch.clear()

    gen_duration = time.time() - start_t
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Done! Generated {num_rows:,} rows in {gen_duration:.2f}s ({file_size_mb:.2f} MB)")
    return output_path


def benchmark_ingestion(csv_path: Path):
    """Benchmarks the streaming ingestion service on the CSV file."""
    print(f"\n--- Benchmarking Ingestion on {csv_path.name} ({os.path.getsize(csv_path)/(1024*1024):.2f} MB) ---")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    upload_id = f"bench-{int(time.time())}"
    try:
        upload = MasterUpload(
            id=upload_id,
            filename=csv_path.name,
            sha256="stress_test_benchmark_sha256",
            uploaded_by="benchmarker",
            status="queued",
        )
        db.add(upload)
        db.commit()

        start_t = time.time()
        MasterImportService.process_upload_task(
            upload_id=upload_id,
            file_path=str(csv_path),
            actor_id="benchmarker",
            actor_org="ORG_DEMO_01",
            actor_role="hr_admin",
        )
        duration = time.time() - start_t

        db.refresh(upload)
        print(f"Ingestion Finished:")
        print(f"  Status:          {upload.status}")
        print(f"  Total Rows:      {upload.total_rows:,}")
        print(f"  Accepted Rows:   {upload.accepted_rows:,}")
        print(f"  Rejected Rows:   {upload.rejected_rows:,}")
        print(f"  Duration:        {duration:.2f} seconds")
        if duration > 0:
            print(f"  Throughput:      {upload.total_rows / duration:,.1f} rows/second")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate and benchmark master HR CSV dataset.")
    parser.add_argument("--rows", type=int, default=10000, help="Number of rows to generate (default: 10,000 for quick dev test; use 500000 for full stress test)")
    parser.add_argument("--benchmark", action="store_true", help="Run ingestion benchmark immediately after generating")
    parser.add_argument("--output", type=str, default="sample-data/master_hr_dataset.csv", help="Output CSV path")
    args = parser.parse_args()

    out_file = Path(args.output)
    generate_stress_csv(out_file, num_rows=args.rows)

    if args.benchmark:
        benchmark_ingestion(out_file)
