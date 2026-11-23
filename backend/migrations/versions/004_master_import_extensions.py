"""004_master_import_extensions

Revision ID: 004_master_import_extensions
Revises: 003_cookie_consent_log
Create Date: 2026-11-22 21:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from app.database import Base
import app.models

revision: str = '004_master_import_extensions'
down_revision: Union[str, None] = '003_cookie_consent_log'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    # 1. Create any missing tables defined in metadata
    Base.metadata.create_all(bind=bind)

    # 2. Add new columns to existing SQLite tables safely
    columns_to_add = [
        ("master_hr_records", "email", "VARCHAR(255)"),
        ("master_hr_records", "project_code", "VARCHAR(64)"),
        ("master_hr_records", "amount", "FLOAT"),
        ("master_hr_records", "expense_category", "VARCHAR(128)"),
        ("master_hr_records", "receipt_attached", "VARCHAR(8)"),
        ("master_hr_records", "overtime_approved", "VARCHAR(8)"),
        ("employees", "manager", "VARCHAR(255)"),
        ("attendance", "hours_total", "NUMERIC(5, 2)"),
        ("attendance", "status", "VARCHAR(64)"),
        ("attendance", "overtime_approved", "VARCHAR(8)"),
        ("timesheets", "hours_total", "NUMERIC(5, 2)"),
        ("timesheets", "status", "VARCHAR(64)"),
        ("expense_claims", "receipt_attached", "VARCHAR(8)"),
        ("audit_flags", "record_id", "VARCHAR(128)"),
    ]

    for table, col, col_type in columns_to_add:
        try:
            bind.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
        except Exception:
            # Column may already exist or table created with it
            pass


def downgrade() -> None:
    pass
