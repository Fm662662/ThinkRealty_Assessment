# models/lead.py
from sqlalchemy import Column, String, Integer, DateTime, ARRAY, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime
from app.db.base_class import Base

class Lead(Base):
    __tablename__ = "leads"

    lead_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_type = Column(String(50), nullable=False, default="Source is None")
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=False)
    nationality = Column(String(100), nullable=True)
    language_preference = Column(String(20), nullable=True)  # 'arabic', 'english'
    budget_min = Column(Integer, nullable=True)
    budget_max = Column(Integer, nullable=True)
    property_type = Column(String(50), nullable=True)  # apartment, villa, townhouse, commercial
    preferred_areas = Column(ARRAY(String), nullable=True)
    status = Column(String(30), nullable=False, default="new")
    lead_score = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("language_preference IN ('arabic','english')", name="chk_lead_language"),
        CheckConstraint("property_type IN ('apartment','villa','townhouse','commercial')", name="chk_lead_property_type"),
        CheckConstraint("status IN ('new','contacted','qualified','viewing_scheduled','negotiation','converted','lost')", name="chk_lead_status"),
        CheckConstraint("lead_score BETWEEN 0 AND 100", name="chk_lead_score"),
        UniqueConstraint("phone", "source_type", name="uq_lead_phone_source"),  # 👈 enforce uniqueness per source

    )

    # Relationships
    sources = relationship("LeadSource", back_populates="lead", cascade="all, delete-orphan")
    assignments = relationship("LeadAssignment", back_populates="lead", cascade="all, delete-orphan")
    follow_up_tasks = relationship("FollowUpTask", back_populates="lead", cascade="all, delete-orphan")
    activities = relationship("LeadActivity", back_populates="lead", cascade="all, delete-orphan")
    property_interests = relationship("LeadPropertyInterest", back_populates="lead", cascade="all, delete-orphan")
    conversion_history = relationship("LeadConversionHistory", back_populates="lead", cascade="all, delete-orphan")

