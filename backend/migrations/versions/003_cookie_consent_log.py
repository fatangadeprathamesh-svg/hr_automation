"""003_cookie_consent_log

Revision ID: 003_cookie_consent_log
Revises: 002_hr_duties_schema
Create Date: 2026-11-22 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from app.database import Base
import app.models

revision: str = '003_cookie_consent_log'
down_revision: Union[str, None] = '002_hr_duties_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    pass
