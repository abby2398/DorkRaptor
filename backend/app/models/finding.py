from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, ForeignKey, JSON
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
from datetime import datetime, timezone
import uuid


class Finding(Base):
    __tablename__ = "findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=True)
    snippet = Column(Text, nullable=True)
    dork_query = Column(Text, nullable=True)

    source = Column(
        SAEnum("google", "bing", "duckduckgo", "yandex", "github", "cloud_scan",
               name="findingsource", create_type=False),
        default="bing",
    )
    category = Column(
        SAEnum("sensitive_files", "admin_panels", "directory_listings", "backup_files",
               "config_files", "credentials", "documents", "database_dumps",
               "cloud_storage", "github_leaks", "api_endpoints", "other",
               name="findingcategory", create_type=False),
        default="other",
    )
    severity = Column(
        SAEnum("critical", "high", "medium", "low", "info",
               name="severity", create_type=False),
        default="info",
    )

    ai_analysis = Column(Text, nullable=True)
    ai_explanation = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=False)
    raw_data = Column(JSON, nullable=True)
    discovered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    scan = relationship("Scan", back_populates="findings")

    def to_dict(self):
        return {
            "id": str(self.id),
            "scan_id": str(self.scan_id),
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "dork_query": self.dork_query,
            "source": self.source,
            "category": self.category,
            "severity": self.severity,
            "ai_analysis": self.ai_analysis,
            "ai_explanation": self.ai_explanation,
            "is_verified": self.is_verified,
            "discovered_at": self.discovered_at.isoformat() if self.discovered_at else None,
        }
