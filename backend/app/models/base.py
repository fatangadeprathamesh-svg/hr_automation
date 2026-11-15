import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ProvenanceMixin:
    """Standard provenance and audit fields required for all imported business records."""
    organization_id = Column(String(64), nullable=False, index=True, default="ORG_DEMO_01")
    source_system = Column(String(64), nullable=False, index=True)
    source_record_id = Column(String(128), nullable=False, index=True)
    source_updated_at = Column(DateTime(timezone=True), nullable=True)
    imported_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    import_id = Column(String(36), ForeignKey("source_imports.import_id"), nullable=False, index=True)
    record_version = Column(Integer, nullable=False, default=1)
    raw_evidence_reference = Column(String(512), nullable=True)
