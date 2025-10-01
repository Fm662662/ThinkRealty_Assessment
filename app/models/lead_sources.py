# models/lead_source.py
from sqlalchemy import Column, String, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime
from app.db.base_class import Base

class LeadSource(Base):
    __tablename__ = "lead_sources"

    source_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.lead_id", ondelete="CASCADE"), nullable=False)
    source_type = Column(String(50), nullable=False)
    campaign_id = Column(String(100), nullable=True)
    referrer_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.agent_id", ondelete="SET NULL"), nullable=True)
    property_id = Column(UUID(as_uuid=True), nullable=True)
    utm_source = Column(String(100), nullable=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "source_type IN ('bayut','propertyFinder','dubizzle','website','walk_in','referral')",
            name="chk_source_type"
        ),
        Index("idx_sources_type", "source_type"),
        Index("idx_sources_campaign", "campaign_id"),
        Index("idx_sources_utm", "utm_source", "utm_medium", "utm_campaign"),
    )

    # Relationships
    lead = relationship("Lead", back_populates="sources")
    referrer_agent = relationship("Agent", back_populates="referred_leads")
