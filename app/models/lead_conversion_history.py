# models/lead_conversion_history.py
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime
from app.db.base_class import Base

class LeadConversionHistory(Base):
    __tablename__ = "lead_conversion_history"

    history_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.lead_id", ondelete="CASCADE"), nullable=False)
    previous_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    changed_by = Column(UUID(as_uuid=True), nullable=True)  # agent_id or supervisor
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    # Relationships
    lead = relationship("Lead", back_populates="conversion_history")

    __table_args__ = (
        Index("idx_history_lead", "lead_id"),
        Index("idx_history_new_status", "new_status"),
        Index("idx_history_time", "changed_at"),
    )
