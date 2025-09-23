# models/agent.py
from sqlalchemy import Column, String, Boolean, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime
from app.db.base_class import Base

class Agent(Base):
    __tablename__ = "agents"

    agent_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    full_name = Column(String(200), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20), nullable=False)
    specialization = Column(String(100), nullable=True)  # e.g., apartment, villa, commercial
    preferred_areas = Column(ARRAY(String), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lead_assignments = relationship("LeadAssignment", back_populates="agent", cascade="all, delete-orphan")
    follow_up_tasks = relationship("FollowUpTask", back_populates="agent", cascade="all, delete-orphan")
    performance_metrics = relationship("AgentPerformanceMetric", back_populates="agent", cascade="all, delete-orphan")

    referred_leads = relationship("LeadSource", back_populates="referrer_agent", cascade="all, delete-orphan")
    lead_activities = relationship("LeadActivity", back_populates="agent", cascade="all, delete-orphan")

    


