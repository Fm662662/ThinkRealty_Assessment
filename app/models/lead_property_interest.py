# models/lead_property_interest.py
from sqlalchemy import Column, String, DateTime, ForeignKey, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime
from app.db.base_class import Base

class LeadPropertyInterest(Base):
    __tablename__ = "lead_property_interests"

    interest_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.lead_id", ondelete="CASCADE"), nullable=False)
    property_id = Column(UUID(as_uuid=True), nullable=False)
    interest_level = Column(String(20), nullable=False)
    noted_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "interest_level IN ('high','medium','low')",
            name="chk_interest_level"
        ),
        UniqueConstraint("lead_id", "property_id", name="unique_lead_property"),
        Index("idx_interest_lead", "lead_id"),
        Index("idx_interest_property", "property_id"),
        Index("idx_interest_level", "interest_level"),
    )

    # Relationships
    lead = relationship("Lead", back_populates="property_interests")
