# models/agent_performance_metric.py
from sqlalchemy import Column, Date, DateTime, Integer, Numeric, Interval, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime
from app.db.base_class import Base

class AgentPerformanceMetric(Base):
    __tablename__ = "agent_performance_metrics"

    metric_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    total_active_leads = Column(Integer, default=0)
    overdue_follow_ups = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    average_response_time = Column(Interval, nullable=True)
    lead_score_average = Column(Integer, nullable=True)
    conversion_rate = Column(Numeric(5,2), nullable=True)
    average_deal_size = Column(Numeric(15,2), nullable=True)
    response_time_rank = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('agent_id', 'date', name='unique_agent_date'),
        Index("idx_metrics_agent", "agent_id"),
        Index("idx_metrics_date", "date"),
        Index("idx_metrics_conversion_rate", "conversion_rate"),
    )

    # Relationships
    agent = relationship("Agent", back_populates="performance_metrics")
