# models/follow_up_task.py
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime
from app.db.base_class import Base

class FollowUpTask(Base):
    __tablename__ = "follow_up_tasks"

    task_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.lead_id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False)
    task_type = Column(String(30), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    completed = Column(Boolean, default=False)
    priority = Column(String(10), default="medium")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # ✅ keep in sync
    completed_at = Column(DateTime, nullable=True)  # ✅ matches schema

    __table_args__ = (
        CheckConstraint(
            "task_type IN ('call','email','whatsapp','viewing','meeting')",
            name="chk_task_type"
        ),
        CheckConstraint(
            "priority IN ('high','medium','low')",
            name="chk_task_priority"
        ),
        Index("idx_tasks_agent", "agent_id"),
        Index("idx_tasks_lead", "lead_id"),
        Index("idx_tasks_due_date", "due_date"),
    )

    # Relationships
    lead = relationship("Lead", back_populates="follow_up_tasks")
    agent = relationship("Agent", back_populates="follow_up_tasks")
