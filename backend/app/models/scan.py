from sqlalchemy import Column, String, DateTime, Text, Integer, JSON
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
from datetime import datetime, timezone
import uuid


class Scan(Base):
    __tablename__ = "scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String(255), nullable=False, index=True)
    status = Column(
        SAEnum("pending", "running", "completed", "failed", "cancelled",
               name="scanstatus", create_type=False),
        default="pending",
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    celery_task_id = Column(String(255), nullable=True)

    total_findings = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    info_count = Column(Integer, default=0)

    dorks_executed = Column(Integer, default=0)
    dorks_total = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    scan_config = Column(JSON, nullable=True)

    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": str(self.id),
            "domain": self.domain,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_findings": self.total_findings or 0,
            "critical_count": self.critical_count or 0,
            "high_count": self.high_count or 0,
            "medium_count": self.medium_count or 0,
            "low_count": self.low_count or 0,
            "info_count": self.info_count or 0,
            "dorks_executed": self.dorks_executed or 0,
            "dorks_total": self.dorks_total or 0,
            "error_message": self.error_message,
        }
