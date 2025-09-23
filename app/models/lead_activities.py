# models/lead_activity.py
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime
from app.db.base_class import Base

class LeadActivity(Base):
    __tablename__ = "lead_activities"

    activity_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.lead_id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False)
    activity_type = Column(String(30), nullable=False)
    notes = Column(Text, nullable=True)
    outcome = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    next_follow_up = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "activity_type IN ('call','email','whatsapp','viewing','meeting','offer_made')",
            name="chk_activity_type"
        ),
        CheckConstraint(
            "outcome IN ('positive','negative','neutral')",
            name="chk_activity_outcome"
        ),
        Index("idx_activity_lead", "lead_id"),
        Index("idx_activity_agent", "agent_id"),
        Index("idx_activity_type", "activity_type"),
        Index("idx_activity_time", "created_at"),
    )

    # Relationships
    lead = relationship("Lead", back_populates="activities")
    agent = relationship("Agent", back_populates="lead_activities")

    agent = relationship("Agent", back_populates="lead_activities")

