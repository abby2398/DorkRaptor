from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
from datetime import datetime, timezone
import uuid


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # null for OAuth users
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)

    role = Column(
        SAEnum("admin", "user", name="userrole", create_type=False),
        default="user",
        nullable=False,
    )

    provider = Column(
        SAEnum("local", "google", name="authprovider", create_type=False),
        default="local",
        nullable=False,
    )
    provider_id = Column(String(255), nullable=True)  # Google sub

    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "avatar_url": self.avatar_url,
            "role": self.role,
            "provider": self.provider,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
