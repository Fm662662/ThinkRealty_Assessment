# crud/agent_performance_metrics.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import List, Optional
from uuid import UUID
from datetime import date

from app.models.agent_performance_metrics import AgentPerformanceMetric


# ---------------- CREATE ----------------
async def create_metric(
    db: AsyncSession,
    agent_id: UUID,
    date: date,
    total_active_leads: int = 0,
    overdue_follow_ups: int = 0,
    conversions: int = 0,
    average_response_time=None,
    lead_score_average: Optional[int] = None,
    conversion_rate: Optional[float] = None,
    average_deal_size: Optional[float] = None,
    response_time_rank: Optional[int] = None,
) -> AgentPerformanceMetric:
    metric = AgentPerformanceMetric(
        agent_id=agent_id,
        date=date,
        total_active_leads=total_active_leads,
        overdue_follow_ups=overdue_follow_ups,
        conversions=conversions,
        average_response_time=average_response_time,
        lead_score_average=lead_score_average,
        conversion_rate=conversion_rate,
        average_deal_size=average_deal_size,
        response_time_rank=response_time_rank,
    )
    db.add(metric)
    await db.commit()
    await db.refresh(metric)
    return metric


# ---------------- READ ----------------
async def get_metric(db: AsyncSession, metric_id: UUID) -> Optional[AgentPerformanceMetric]:
    result = await db.execute(
        select(AgentPerformanceMetric).where(AgentPerformanceMetric.metric_id == metric_id)
    )
    return result.scalar_one_or_none()


async def get_metrics_by_agent(db: AsyncSession, agent_id: UUID) -> List[AgentPerformanceMetric]:
    result = await db.execute(
        select(AgentPerformanceMetric).where(AgentPerformanceMetric.agent_id == agent_id)
    )
    return result.scalars().all()


async def get_metric_by_agent_and_date(
    db: AsyncSession, agent_id: UUID, metric_date: date
) -> Optional[AgentPerformanceMetric]:
    result = await db.execute(
        select(AgentPerformanceMetric).where(
            AgentPerformanceMetric.agent_id == agent_id,
            AgentPerformanceMetric.date == metric_date
        )
    )
    return result.scalar_one_or_none()


# ---------------- UPDATE ----------------
async def update_metric(
    db: AsyncSession,
    metric_id: UUID,
    **kwargs
) -> Optional[AgentPerformanceMetric]:
    """
    kwargs can include: total_active_leads, overdue_follow_ups, conversions,
    average_response_time, lead_score_average, conversion_rate,
    average_deal_size, response_time_rank
    """
    result = await db.execute(
        update(AgentPerformanceMetric)
        .where(AgentPerformanceMetric.metric_id == metric_id)
        .values(**kwargs)
        .returning(AgentPerformanceMetric)
    )
    await db.commit()
    return result.scalar_one_or_none()


# ---------------- DELETE ----------------
async def delete_metric(db: AsyncSession, metric_id: UUID) -> bool:
    result = await db.execute(
        delete(AgentPerformanceMetric).where(AgentPerformanceMetric.metric_id == metric_id)
    )
    await db.commit()
    return result.rowcount > 0
