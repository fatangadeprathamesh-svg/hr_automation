import os
import logging
from datetime import date
from sqlalchemy.orm import Session
from app.database import Base, engine, SessionLocal
from app.models.hr import Employee, PolicyVersion, Attendance
from app.imports.service import IngestionService
from app.rules.engine import DEFAULT_POLICY_VERSION, DEFAULT_POLICY_CONFIG

logger = logging.getLogger(__name__)


def init_db_and_seed():
    """Ensures tables exist and seeds baseline personas and sample data."""
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # 1. Seed default personas if employees table is empty
        if db.query(Employee).count() == 0:
            mgr1 = Employee(
                employee_id="MGR001",
                organization_id="ORG_DEMO_01",
                email="bob.manager@example.com",
                full_name="Bob Manager",
                manager_id=None,
                timezone="America/New_York",
                hire_date=date(2024, 3, 1),
                is_active=True,
            )
            hr1 = Employee(
                employee_id="HR001",
                organization_id="ORG_DEMO_01",
                email="carol.hr@example.com",
                full_name="Carol HR Admin",
                manager_id=None,
                timezone="America/New_York",
                hire_date=date(2023, 6, 1),
                is_active=True,
            )
            emp1 = Employee(
                employee_id="EMP001",
                organization_id="ORG_DEMO_01",
                email="alice@example.com",
                full_name="Alice Employee",
                manager_id="MGR001",
                timezone="America/New_York",
                hire_date=date(2025, 1, 15),
                is_active=True,
            )
            db.add_all([mgr1, hr1, emp1])
            db.commit()
            logger.info("Seeded default employees: MGR001, HR001, EMP001")

        # 2. Ensure default policy version
        policy = db.query(PolicyVersion).filter(PolicyVersion.policy_version == DEFAULT_POLICY_VERSION).first()
        if not policy:
            policy = PolicyVersion(
                policy_version=DEFAULT_POLICY_VERSION,
                effective_from=date(2026, 1, 1),
                effective_to=None,
                rule_configurations=DEFAULT_POLICY_CONFIG,
                is_active=True,
            )
            db.add(policy)
            db.commit()
            logger.info("Seeded default policy: %s", DEFAULT_POLICY_VERSION)

        # 3. Seed sample data if attendance is empty
        if db.query(Attendance).count() == 0:
            sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sample-data"))
            if os.path.exists(sample_dir):
                feeds = [
                    ("attendance", "attendance_valid.csv"),
                    ("leave", "leave_valid.csv"),
                    ("timesheets", "timesheets_valid.csv"),
                    ("expense_claims", "expense_claims_valid.csv"),
                    ("documents", "documents_valid.csv"),
                ]
                for system, filename in feeds:
                    path = os.path.join(sample_dir, filename)
                    if os.path.exists(path):
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                        IngestionService.ingest_csv(
                            db=db,
                            organization_id="ORG_DEMO_01",
                            source_system=system,
                            covered_period="2026-10",
                            file_content=content,
                            actor_id="service:init_seed",
                            raw_file_uri=f"sample-data/{filename}",
                            is_complete_feed=True,
                        )
                logger.info("Successfully ingested all valid sample-data feeds for period 2026-10")

    except Exception as e:
        db.rollback()
        logger.warning("Database seed notice: %s", e)
    finally:
        db.close()
