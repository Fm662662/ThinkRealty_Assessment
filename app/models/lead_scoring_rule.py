# models/lead_scoring_rule.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from uuid import uuid4
from datetime import datetime
from app.db.base_class import Base

class LeadScoringRule(Base):
    __tablename__ = "lead_scoring_rules"

    rule_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    rule_name = Column(String(100), nullable=False)
    criteria = Column(JSONB, nullable=False)  # JSON-based flexible rules
    score_delta = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_scoring_rules_active", "is_active"),
        Index("idx_scoring_rules_criteria", "criteria", postgresql_using="gin"),
    )
