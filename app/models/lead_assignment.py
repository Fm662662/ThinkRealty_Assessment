# models/lead_assignment.py
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime
from app.db.base_class import Base

class LeadAssignment(Base):
    __tablename__ = "lead_assignments"

    assignment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.lead_id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    reassigned = Column(Boolean, default=False)
    reason = Column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("lead_id", "agent_id", "assigned_at", name="unique_lead_assignment"),
        Index("idx_assignment_agent", "agent_id"),
        Index("idx_assignment_lead", "lead_id"),
        Index("idx_assignment_time", "assigned_at"),
    )

    # Relationships
    lead = relationship("Lead", back_populates="assignments")
    agent = relationship("Agent", back_populates="lead_assignments")
